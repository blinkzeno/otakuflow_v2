-- Otakuflow schema. Source of truth. Applied by backend/db/database.py.
-- SQLite dialect. All file paths stored here are relative to DATA_DIR.

CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'created',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chapters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  source_filename TEXT NOT NULL,
  page_count INTEGER NOT NULL DEFAULT 0,
  reading_order TEXT NOT NULL DEFAULT 'ltr',
  chapter_summary TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  page_index INTEGER NOT NULL,
  page_id TEXT NOT NULL UNIQUE,
  filename TEXT NOT NULL,
  rel_path TEXT NOT NULL,
  width INTEGER,
  height INTEGER,
  analysis_json TEXT,
  importance INTEGER,
  analysis_status TEXT NOT NULL DEFAULT 'pending',
  analysis_error TEXT
);

CREATE TABLE IF NOT EXISTS script_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  segment_key TEXT NOT NULL UNIQUE,
  text TEXT NOT NULL,
  page_refs TEXT NOT NULL DEFAULT '[]',
  duration_estimate REAL,
  status TEXT NOT NULL DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS audio_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  segment_id INTEGER NOT NULL REFERENCES script_segments(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  voice TEXT NOT NULL,
  rel_path TEXT NOT NULL,
  duration REAL NOT NULL,
  text_hash TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS renders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  timeline_json TEXT NOT NULL,
  video_rel_path TEXT,
  settings_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
  stage TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  progress INTEGER NOT NULL DEFAULT 0,
  log_path TEXT,
  error TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_costs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  kind TEXT NOT NULL,
  units_json TEXT NOT NULL DEFAULT '{}',
  cost_usd REAL NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pages_chapter ON pages(chapter_id, page_index);
CREATE INDEX IF NOT EXISTS idx_segments_chapter ON script_segments(chapter_id, position);
CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id, stage);
CREATE INDEX IF NOT EXISTS idx_costs_chapter ON ai_costs(chapter_id);
