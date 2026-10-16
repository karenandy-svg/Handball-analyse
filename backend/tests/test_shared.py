"""Integration tests for shared-game API. Run with python -m unittest discover -s backend/tests."""
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from backend import database
from backend.main import app
from backend.security import hash_password

ORIGIN = {"Origin": "https://wurfbilder.duckdns.org"}

class SharedApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.temp.name) / "test.db"
        database.initialize()
        with database.connect() as db:
            db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                       ("trainer", hash_password("secure-test-password"), "trainer"))
        self.client = TestClient(app, base_url="https://wurfbilder.duckdns.org")
        response = self.client.post("/api/auth/login", headers=ORIGIN,
                                    json={"username": "trainer", "password": "secure-test-password"})
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_idempotent_shot_and_version_conflict(self):
        created = self.client.post("/api/games", headers=ORIGIN, json={"id":"g1","data":{"name":"Test"}})
        self.assertEqual(created.status_code, 201)
        locked = self.client.post("/api/games/g1/lock", headers=ORIGIN)
        self.assertEqual(locked.status_code, 200)
        token = locked.json()["lock_token"]
        operation = {"operation_id":"op-12345678","lock_token":token,"base_version":0,
                     "kind":"shot.upsert","item_id":"shot-1","data":{"result":"goal"}}
        first = self.client.post("/api/games/g1/mutations", headers=ORIGIN, json=operation)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["version"], 1)
        retry = self.client.post("/api/games/g1/mutations", headers=ORIGIN, json=operation)
        self.assertTrue(retry.json()["duplicate"])
        conflict = dict(operation, operation_id="op-87654321")
        self.assertEqual(self.client.post("/api/games/g1/mutations", headers=ORIGIN,
                                          json=conflict).status_code, 409)
        games = self.client.get("/api/games").json()
        self.assertEqual(len(games[0]["data"]["shots"]), 1)

    def test_lock_rejects_second_editor(self):
        self.client.post("/api/games", headers=ORIGIN, json={"id":"g2","data":{}})
        self.assertEqual(self.client.post("/api/games/g2/lock", headers=ORIGIN).status_code, 200)
        self.assertEqual(self.client.post("/api/games/g2/lock", headers=ORIGIN).status_code, 423)

if __name__ == "__main__":
    unittest.main()
