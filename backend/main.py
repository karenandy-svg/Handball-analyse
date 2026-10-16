"""Phase 1: authentication API. Do not expose the existing static app until protected routing is configured."""
import os
from pathlib import Path
import re
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from .database import connect, initialize
from .security import hash_password, new_session_token, token_hash, verify_password

COOKIE = "wurfbild_session"
SESSION_SECONDS = 12 * 60 * 60
LOGIN_ATTEMPTS = defaultdict(deque)

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield

app = FastAPI(title="WURFBILD API", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=1024)

class NewUser(Credentials):
    role: str = "trainer"

def check_origin(request: Request):
    expected = os.environ.get("WURFBILD_ORIGIN", "https://wurfbilder.duckdns.org")
    origin = request.headers.get("origin")
    if origin != expected:
        raise HTTPException(403, "Invalid request origin")

def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Authentication required")
    with connect() as db:
        user = db.execute("""
            SELECT u.id, u.username, u.role FROM sessions s
            JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_at > unixepoch() AND u.active=1
        """, (token_hash(token),)).fetchone()
    if user is None:
        raise HTTPException(401, "Session expired")
    return dict(user)

def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Administrator required")
    return user

@app.post("/api/auth/login")
def login(credentials: Credentials, request: Request, response: Response):
    check_origin(request)
    now = time.monotonic()
    key = (request.client.host if request.client else "unknown", credentials.username.casefold())
    attempts = LOGIN_ATTEMPTS[key]
    while attempts and now - attempts[0] > 900:
        attempts.popleft()
    if len(attempts) >= 8:
        raise HTTPException(429, "Too many attempts. Try later.")
    attempts.append(now)
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE username=? AND active=1", (credentials.username,)).fetchone()
        if user is None or not verify_password(user["password_hash"], credentials.password):
            raise HTTPException(401, "Invalid credentials")
        attempts.clear()
        token = new_session_token()
        db.execute("DELETE FROM sessions WHERE expires_at <= unixepoch()")
        db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,unixepoch()+?)",
                   (token_hash(token), user["id"], SESSION_SECONDS))
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, secure=True, httponly=True,
                        samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"id": user["id"], "username": user["username"], "role": user["role"]}

@app.get("/api/auth/me")
def me(response: Response, user=Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user

@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    check_origin(request)
    token = request.cookies.get(COOKIE)
    if token:
        with connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))
    response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="strict")

@app.get("/api/admin/users")
def list_users(admin=Depends(require_admin)):
    with connect() as db:
        rows = db.execute("SELECT id,username,role,active,created_at FROM users ORDER BY username").fetchall()
    return [dict(row) for row in rows]

@app.post("/api/admin/users", status_code=201)
def create_user(payload: NewUser, request: Request, admin=Depends(require_admin)):
    check_origin(request)
    if payload.role not in ("admin", "trainer") or not re.fullmatch(r"[A-Za-z0-9_.-]{3,80}", payload.username):
        raise HTTPException(422, "Invalid username or role")
    try:
        password = hash_password(payload.password)
        with connect() as db:
            cursor = db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                                (payload.username, password, payload.role))
            return {"id": cursor.lastrowid, "username": payload.username, "role": payload.role}
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username already exists")

# Register API routes before the catch-all static GET route.
from .shared import router as shared_router
app.include_router(shared_router)
from .handball4all import router as handball4all_router
app.include_router(handball4all_router)

# Nginx must proxy ALL paths here, never expose the dist directory directly.
STATIC_ROOT = Path(__file__).resolve().parent.parent / "dist"
PUBLIC_FILES = {"/login.html", "/login.css", "/login.js", "/icon.svg"}

@app.get("/{asset_path:path}", include_in_schema=False)
def serve_app(asset_path: str, request: Request):
    requested = "/" + asset_path
    if requested == "/login":
        requested = "/login.html"
    if requested in PUBLIC_FILES:
        target = STATIC_ROOT / requested.lstrip("/")
    else:
        try:
            current_user(request)
        except HTTPException:
            return RedirectResponse("/login.html", status_code=303)
        if requested in ("/", "/index.html"):
            requested = "/index.html"
        target = (STATIC_ROOT / requested.lstrip("/")).resolve()
        if not target.is_relative_to(STATIC_ROOT.resolve()):
            raise HTTPException(404)
    if not target.is_file():
        raise HTTPException(404)
    response = FileResponse(target)
    response.headers["Cache-Control"] = "no-store, private"
    return response
