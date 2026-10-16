"""Run on server: python -m backend.create_admin <username> (password entered securely)."""
import getpass
import re
import sys
from .database import connect, initialize
from .security import hash_password

def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"[A-Za-z0-9_.-]{3,80}", sys.argv[1]):
        raise SystemExit("Usage: python -m backend.create_admin <username>")
    password = getpass.getpass("New admin password (min 12 chars): ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match")
    password_hash = hash_password(password)
    initialize()
    with connect() as db:
        db.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,'admin')",
                   (sys.argv[1], password_hash))
    print("Administrator created")

if __name__ == "__main__":
    main()
