"""Run: python -m unittest discover -s backend/tests -v (requires httpx)."""
import os
import tempfile
import unittest

from fastapi.testclient import TestClient
from backend import database
from backend.main import app
from backend.security import hash_password

ORIGIN = "https://wurfbilder.duckdns.org"

class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database.DB_PATH = __import__("pathlib").Path(self.temp.name) / "test.sqlite3"
        database.initialize()
        with database.connect() as db:
            db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                       ("admin", hash_password("long-secure-test-password"), "admin"))
            db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                       ("trainer", hash_password("another-secure-test-password"), "trainer"))
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_unauthenticated_app_redirects(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login.html")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_login_requires_origin_and_valid_credentials(self):
        self.assertEqual(self.client.post("/api/auth/login", json={
            "username":"admin", "password":"long-secure-test-password"
        }).status_code, 403)
        self.assertEqual(self.client.post("/api/auth/login", headers={"Origin":ORIGIN}, json={
            "username":"admin", "password":"wrong"
        }).status_code, 401)
        response = self.client.post("/api/auth/login", headers={"Origin":ORIGIN}, json={
            "username":"admin", "password":"long-secure-test-password"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("httponly", response.headers["set-cookie"].lower())
        self.assertIn("secure", response.headers["set-cookie"].lower())
        self.assertEqual(self.client.get("/api/auth/me").json()["role"], "admin")

    def test_trainer_cannot_manage_users(self):
        self.client.post("/api/auth/login", headers={"Origin":ORIGIN}, json={
            "username":"trainer", "password":"another-secure-test-password"
        })
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
        self.assertEqual(self.client.post("/api/admin/users", headers={"Origin":ORIGIN}, json={
            "username":"newtrainer", "password":"very-long-password", "role":"trainer"
        }).status_code, 403)

    def test_admin_can_create_user_and_logout(self):
        self.client.post("/api/auth/login", headers={"Origin":ORIGIN}, json={
            "username":"admin", "password":"long-secure-test-password"
        })
        response = self.client.post("/api/admin/users", headers={"Origin":ORIGIN}, json={
            "username":"newtrainer", "password":"very-long-password", "role":"trainer"
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout", headers={"Origin":ORIGIN}).status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

if __name__ == "__main__":
    unittest.main()
