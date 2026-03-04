"""
database.py — ініціалізація SQLite з WAL-режимом
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("database.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS personnel (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pib         TEXT NOT NULL,
            phone       TEXT,
            rank        TEXT,
            birth_date  TEXT,
            location    TEXT,
            subdivision TEXT,
            arrival_date TEXT,
            enroll_date TEXT,
            source_hash TEXT UNIQUE   -- MD5 рядка для дедупликації
        );

        CREATE INDEX IF NOT EXISTS idx_personnel_pib
            ON personnel(pib COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_personnel_phone
            ON personnel(phone);

        CREATE TABLE IF NOT EXISTS documents (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL REFERENCES personnel(id),
            doc_type     TEXT NOT NULL,   -- аналізи | влк | стаціонар | характеристика | рапорт
            diagnosis    TEXT NOT NULL,
            file_path    TEXT,
            created_at   TEXT NOT NULL DEFAULT (date('now')),
            created_by   TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_docs_personnel
            ON documents(personnel_id);
        CREATE INDEX IF NOT EXISTS idx_docs_type
            ON documents(doc_type);

        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            action     TEXT NOT NULL,    -- import | create_doc | export
            detail     TEXT,
            username   TEXT,
            ts         TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role         TEXT NOT NULL DEFAULT 'operator'  -- admin | operator
        );
        """)
    print(f"[DB] Ініціалізовано: {DB_PATH.resolve()}")
