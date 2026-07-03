# -*- coding: utf-8 -*-
import sqlite3
import datetime
from config import DB_PATH

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()


def init_db():
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            ban_status TEXT DEFAULT 'none',      -- none / soft / hard
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            answer_text TEXT,
            status TEXT DEFAULT 'pending',        -- pending / approved / rejected
            group_msg_id INTEGER,
            admin_id INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,                            -- appeal / complaint / other
            text TEXT,
            status TEXT DEFAULT 'pending',        -- pending / answered / rejected / banned
            group_msg_id INTEGER,
            admin_reply TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()

    # дефолтные настройки
    if get_setting("recruitment_open") is None:
        set_setting("recruitment_open", "0")
    if get_setting("anketa_template") is None:
        set_setting("anketa_template", "")
    if get_setting("anketa_photo") is None:
        set_setting("anketa_photo", "")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ==================== SETTINGS ====================

def get_setting(key: str):
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else None


def set_setting(key: str, value: str):
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


# ==================== USERS ====================

def add_user(user_id: int, username: str, full_name: str):
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, now()),
        )
        conn.commit()


def get_user(user_id: int):
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()


def set_ban_status(user_id: int, status: str):
    cur.execute("UPDATE users SET ban_status = ? WHERE user_id = ?", (status, user_id))
    conn.commit()


def get_banned_users():
    cur.execute("SELECT * FROM users WHERE ban_status != 'none'")
    return cur.fetchall()


# ==================== APPLICATIONS (АНКЕТЫ) ====================

def create_application(user_id, answer_text):
    cur.execute(
        "INSERT INTO applications (user_id, answer_text, created_at) VALUES (?, ?, ?)",
        (user_id, answer_text, now()),
    )
    conn.commit()
    return cur.lastrowid


def set_application_group_msg(app_id, msg_id):
    cur.execute("UPDATE applications SET group_msg_id = ? WHERE id = ?", (msg_id, app_id))
    conn.commit()


def set_application_status(app_id, status, admin_id=None):
    cur.execute(
        "UPDATE applications SET status = ?, admin_id = ? WHERE id = ?",
        (status, admin_id, app_id),
    )
    conn.commit()


def get_application(app_id):
    cur.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    return cur.fetchone()


def get_applications_by_status(status):
    cur.execute("SELECT * FROM applications WHERE status = ? ORDER BY id DESC", (status,))
    return cur.fetchall()


def get_applications_processed():
    cur.execute(
        "SELECT * FROM applications WHERE status != 'pending' ORDER BY id DESC"
    )
    return cur.fetchall()


# ==================== TICKETS (ПОДДЕРЖКА) ====================

def create_ticket(user_id, ticket_type, text):
    cur.execute(
        "INSERT INTO tickets (user_id, type, text, created_at) VALUES (?, ?, ?, ?)",
        (user_id, ticket_type, text, now()),
    )
    conn.commit()
    return cur.lastrowid


def set_ticket_group_msg(ticket_id, msg_id):
    cur.execute("UPDATE tickets SET group_msg_id = ? WHERE id = ?", (msg_id, ticket_id))
    conn.commit()


def set_ticket_status(ticket_id, status, admin_reply=None):
    cur.execute(
        "UPDATE tickets SET status = ?, admin_reply = ? WHERE id = ?",
        (status, admin_reply, ticket_id),
    )
    conn.commit()


def get_ticket(ticket_id):
    cur.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    return cur.fetchone()


def get_tickets_by_status(status):
    cur.execute("SELECT * FROM tickets WHERE status = ? ORDER BY id DESC", (status,))
    return cur.fetchall()


def get_tickets_processed():
    cur.execute("SELECT * FROM tickets WHERE status != 'pending' ORDER BY id DESC")
    return cur.fetchall()


def get_last_ticket_by_user(user_id):
    cur.execute(
        "SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    )
    return cur.fetchone()
