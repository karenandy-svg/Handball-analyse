CREATE TABLE IF NOT EXISTS shared_teams (
 id TEXT PRIMARY KEY,
 data TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS shared_games (
 id TEXT PRIMARY KEY,
 data TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 0,
 editor_user_id INTEGER REFERENCES users(id),
 lock_token TEXT,
 lock_expires_at INTEGER
);
CREATE TABLE IF NOT EXISTS game_operations (
 game_id TEXT NOT NULL REFERENCES shared_games(id) ON DELETE CASCADE,
 operation_id TEXT NOT NULL,
 version INTEGER NOT NULL,
 PRIMARY KEY(game_id, operation_id)
);
