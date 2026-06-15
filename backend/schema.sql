PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT,
  status TEXT,
  mode TEXT,
  category TEXT,
  items INTEGER DEFAULT 0,
  latency_ms INTEGER DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  source_id TEXT,
  source_name TEXT,
  category TEXT,
  authority TEXT,
  title TEXT NOT NULL,
  url TEXT,
  published_at TEXT,
  tags_json TEXT,
  scene TEXT,
  consulting_value TEXT,
  public_value TEXT,
  ingestion TEXT,
  score INTEGER DEFAULT 0,
  content_hash TEXT,
  inserted_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_type TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  item_count INTEGER DEFAULT 0,
  source_count INTEGER DEFAULT 0,
  added_count INTEGER DEFAULT 0,
  message TEXT
);

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'public',
  industry TEXT DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlists (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  keywords_json TEXT NOT NULL,
  categories_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_items (
  user_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  saved_at TEXT NOT NULL,
  PRIMARY KEY (user_id, item_id)
);

CREATE TABLE IF NOT EXISTS briefs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  brief_type TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  summary TEXT NOT NULL,
  items_json TEXT NOT NULL
);

