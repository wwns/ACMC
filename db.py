"""
Moduł bazy danych (SQLite) dla aplikacji ACMC.
Tworzy tabele: logs, scans, tests
Funkcje: init_db(path), get_conn(), log_event(...), save_scan_result(...), save_test_result(...)
"""
import sqlite3
import threading
from typing import Optional

_db_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def init_db(path: str = 'acmc_data.db'):
    global _conn
    with _db_lock:
        if _conn:
            return
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        cur = _conn.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT
        )
        ''')
        cur.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            host TEXT,
            port INTEGER,
            unit INTEGER,
            ok INTEGER,
            details TEXT
        )
        ''')
        cur.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            host TEXT,
            port INTEGER,
            unit INTEGER,
            name TEXT,
            success INTEGER,
            details TEXT
        )
        ''')
        _conn.commit()


def get_conn():
    global _conn
    if not _conn:
        init_db()
    return _conn


def log_event(level: str, message: str):
    conn = get_conn()
    with _db_lock:
        conn.execute('INSERT INTO logs (level, message) VALUES (?, ?)', (level, message))
        conn.commit()


def save_scan_result(host: str, port: int, unit: int, ok: bool, details: str = ''):
    conn = get_conn()
    with _db_lock:
        conn.execute('INSERT INTO scans (host, port, unit, ok, details) VALUES (?, ?, ?, ?, ?)',
                     (host, port, unit, 1 if ok else 0, details))
        conn.commit()


def save_test_result(host: str, port: int, unit: int, name: str, success: bool, details: str = ''):
    conn = get_conn()
    with _db_lock:
        conn.execute('INSERT INTO tests (host, port, unit, name, success, details) VALUES (?, ?, ?, ?, ?, ?)',
                     (host, port, unit, name, 1 if success else 0, details))
        conn.commit()
