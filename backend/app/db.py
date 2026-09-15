"""SQLite 数据访问层：机型、部件、证据、选定组合、复装步骤。"""
import os
import sqlite3

DB_PATH = os.environ.get(
    "WASHER_DB",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "washer.db"),
)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS machines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_name TEXT NOT NULL,
  revision_code TEXT NOT NULL,
  rated_pressure_bar REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS parts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  part_type TEXT NOT NULL,            -- gun | lance | hose_connector | o_ring
  in_type TEXT, in_gender TEXT,       -- m22 | quick | bayonet ; male | female
  out_type TEXT, out_gender TEXT,
  thread_core_mm REAL,                -- M22 螺纹芯径
  quick_mm REAL,                      -- 快插直径
  bayonet_ear_mm REAL,                -- 卡口耳宽
  spigot_depth_mm REAL,               -- 母端止口深度
  insert_length_mm REAL,              -- 公端插入长度
  groove_cross_mm REAL,               -- 公端密封沟槽截面
  oring_cross_mm REAL,                -- 密封圈截面
  min_pressure_bar REAL NOT NULL,     -- 该段最低耐压
  brand TEXT,                         -- 仅展示，绝不参与判定
  appearance TEXT,                    -- 仅展示，绝不参与判定
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  kind TEXT NOT NULL DEFAULT 'measurement',
  key TEXT NOT NULL,
  value REAL NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(machine_id, key)
);

CREATE TABLE IF NOT EXISTS selections (
  machine_id INTEGER PRIMARY KEY REFERENCES machines(id) ON DELETE CASCADE,
  combo_key TEXT NOT NULL,
  part_ids TEXT NOT NULL,             -- JSON: {gun, lance, hose_connector, o_ring}
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS steps (
  machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  step_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',   -- pending | confirmed | failed
  checks_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (machine_id, step_key)
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def rows(conn: sqlite3.Connection, sql: str, params=()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def row(conn: sqlite3.Connection, sql: str, params=()) -> dict | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None
