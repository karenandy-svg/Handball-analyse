"""Shared game data API; writes are versioned and idempotent."""
import json
import secrets
import sqlite3
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .database import connect
from .main import current_user, check_origin

router = APIRouter(prefix="/api")
LEASE_SECONDS = 604800

class Record(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    data: dict

class Operation(BaseModel):
    operation_id: str = Field(min_length=8, max_length=100)
    lock_token: str = Field(min_length=20, max_length=200)
    base_version: int = Field(ge=0)
    kind: str
    item_id: str = Field(min_length=1, max_length=100)
    data: dict | None = None

class LockToken(BaseModel):
    lock_token: str

@router.get("/teams")
def list_teams(user=Depends(current_user)):
    with connect() as db:
        rows = db.execute("SELECT * FROM shared_teams").fetchall()
    return [{"id": r["id"], "data": json.loads(r["data"]), "version": r["version"]} for r in rows]

@router.post("/teams", status_code=201)
def create_team(payload: Record, request: Request, user=Depends(current_user)):
    check_origin(request)
    try:
        with connect() as db:
            db.execute("INSERT INTO shared_teams(id,data) VALUES(?,?)",
                       (payload.id, json.dumps(payload.data)))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Team already exists")
    return {"id": payload.id, "version": 1}

class TeamUpdate(BaseModel):
    data: dict
    base_version: int = Field(ge=1)

@router.put("/teams/{team_id}")
def update_team(team_id: str, payload: TeamUpdate, request: Request, user=Depends(current_user)):
    check_origin(request)
    with connect() as db:
        result = db.execute(
            "UPDATE shared_teams SET data=?, version=version+1 WHERE id=? AND version=?",
            (json.dumps(payload.data), team_id, payload.base_version),
        )
        if result.rowcount != 1:
            exists = db.execute("SELECT 1 FROM shared_teams WHERE id=?", (team_id,)).fetchone()
            raise HTTPException(409 if exists else 404, "Team version conflict" if exists else "Team not found")
    return {"id": team_id, "version": payload.base_version + 1}

@router.get("/games")
def list_games(user=Depends(current_user)):
    with connect() as db:
        rows = db.execute("SELECT id,data,version,editor_user_id,lock_expires_at FROM shared_games").fetchall()
    return [{"id": r["id"], "data": json.loads(r["data"]), "version": r["version"],
             "editor_user_id": r["editor_user_id"], "lock_expires_at": r["lock_expires_at"]} for r in rows]

@router.post("/games", status_code=201)
def create_game(payload: Record, request: Request, user=Depends(current_user)):
    check_origin(request)
    data = dict(payload.data)
    data["shots"] = []
    data["events"] = []
    try:
        with connect() as db:
            db.execute("INSERT INTO shared_games(id,data) VALUES(?,?)",
                       (payload.id, json.dumps(data)))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Game already exists")
    return {"id": payload.id, "version": 0}

@router.post("/games/{game_id}/lock")
def lock_game(game_id: str, request: Request, user=Depends(current_user)):
    check_origin(request)
    now = int(time.time())
    token = secrets.token_urlsafe(32)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT editor_user_id,lock_expires_at FROM shared_games WHERE id=?", (game_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Game not found")
        if row["editor_user_id"] is not None and (row["lock_expires_at"] or 0) > now:
            raise HTTPException(423, "Game already locked")
        db.execute("UPDATE shared_games SET editor_user_id=?,lock_token=?,lock_expires_at=? WHERE id=?",
                   (user["id"], token, now + LEASE_SECONDS, game_id))
    return {"lock_token": token, "expires_at": now + LEASE_SECONDS}

@router.post("/games/{game_id}/mutations")
def apply_operation(game_id: str, payload: Operation, request: Request, user=Depends(current_user)):
    check_origin(request)
    if payload.kind not in ("shot.upsert", "shot.delete", "event.upsert", "event.delete"):
        raise HTTPException(422, "Unsupported operation")
    if payload.kind.endswith("upsert") and not isinstance(payload.data, dict):
        raise HTTPException(422, "Missing item data")
    now = int(time.time())
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM shared_games WHERE id=?", (game_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Game not found")
        if row["editor_user_id"] != user["id"] or row["lock_token"] != payload.lock_token or (row["lock_expires_at"] or 0) <= now:
            raise HTTPException(423, "No valid edit lock")
        previous = db.execute("SELECT version FROM game_operations WHERE game_id=? AND operation_id=?",
                              (game_id, payload.operation_id)).fetchone()
        if previous:
            return {"version": previous["version"], "duplicate": True}
        if row["version"] != payload.base_version:
            raise HTTPException(409, detail={"server_version": row["version"]})
        game = json.loads(row["data"])
        field = "shots" if payload.kind.startswith("shot.") else "events"
        entries = game.setdefault(field, [])
        entries[:] = [item for item in entries if item.get("id") != payload.item_id]
        if payload.kind.endswith("upsert"):
            item = dict(payload.data)
            item["id"] = payload.item_id
            entries.append(item)
        version = row["version"] + 1
        db.execute("UPDATE shared_games SET data=?,version=?,lock_expires_at=? WHERE id=?",
                   (json.dumps(game), version, now + LEASE_SECONDS, game_id))
        db.execute("INSERT INTO game_operations(game_id,operation_id,version) VALUES(?,?,?)",
                   (game_id, payload.operation_id, version))
    return {"version": version, "duplicate": False}

@router.post("/games/{game_id}/unlock")
def unlock_game(game_id: str, payload: LockToken, request: Request, user=Depends(current_user)):
    check_origin(request)
    with connect() as db:
        cursor = db.execute("""UPDATE shared_games
            SET editor_user_id=NULL,lock_token=NULL,lock_expires_at=NULL
            WHERE id=? AND editor_user_id=? AND lock_token=?""",
            (game_id, user["id"], payload.lock_token))
        if cursor.rowcount != 1:
            raise HTTPException(423, "No valid edit lock")
    return {"ok": True}
