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

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            bio TEXT,
            photo_file_id TEXT
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            answer_text TEXT,
            photo_file_id TEXT,
            status TEXT DEFAULT 'pending',        -- pending / approved / rejected
            admin_id INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,                            -- appeal / complaint / other
            text TEXT,
            status TEXT DEFAULT 'pending',        -- pending / answered / rejected / banned
            admin_reply TEXT,
            created_at TEXT
        );

        -- Карточки-уведомления: любая "живая" карточка заявки/обращения
        -- (в группе или в личке у конкретного админа). Когда заявку решают,
        -- по этой таблице находим все её копии и убираем/удаляем их разом.
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT,                     -- application / ticket
            entity_id INTEGER,
            chat_id INTEGER,
            message_id INTEGER,
            kind TEXT                             -- group / dm
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
    if get_setting("invite_link") is None:
        set_setting("invite_link", "")


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
    else:
        # обновляем юзернейм/имя на случай, если человек их поменял
        cur.execute(
            "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
            (username, full_name, user_id),
        )
        conn.commit()


def get_user(user_id: int):
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()


def get_user_by_username(username: str):
    username = username.lstrip("@")
    cur.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
    return cur.fetchone()


def set_ban_status(user_id: int, status: str):
    cur.execute("UPDATE users SET ban_status = ? WHERE user_id = ?", (status, user_id))
    conn.commit()


def get_banned_users():
    cur.execute("SELECT * FROM users WHERE ban_status != 'none'")
    return cur.fetchall()


# ==================== ПРОФИЛИ ====================

def get_profile(user_id: int):
    cur.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        return row
    return (user_id, None, None)


def set_profile_bio(user_id: int, bio: str):
    cur.execute(
        "INSERT INTO user_profiles (user_id, bio) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET bio = excluded.bio",
        (user_id, bio),
    )
    conn.commit()


def set_profile_photo(user_id: int, photo_file_id: str):
    cur.execute(
        "INSERT INTO user_profiles (user_id, photo_file_id) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET photo_file_id = excluded.photo_file_id",
        (user_id, photo_file_id),
    )
    conn.commit()


# ==================== APPLICATIONS (АНКЕТЫ) ====================

def create_application(user_id, answer_text, photo_file_id=None):
    cur.execute(
        "INSERT INTO applications (user_id, answer_text, photo_file_id, created_at) VALUES (?, ?, ?, ?)",
        (user_id, answer_text, photo_file_id, now()),
    )
    conn.commit()
    return cur.lastrowid


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


# ==================== КАРТОЧКИ-УВЕДОМЛЕНИЯ ====================

def register_card(entity_type, entity_id, chat_id, message_id, kind):
    cur.execute(
        "INSERT INTO cards (entity_type, entity_id, chat_id, message_id, kind) VALUES (?, ?, ?, ?, ?)",
        (entity_type, entity_id, chat_id, message_id, kind),
    )
    conn.commit()


def get_cards(entity_type, entity_id):
    cur.execute(
        "SELECT * FROM cards WHERE entity_type = ? AND entity_id = ?",
        (entity_type, entity_id),
    )
    return cur.fetchall()


def clear_cards(entity_type, entity_id):
    cur.execute(
        "DELETE FROM cards WHERE entity_type = ? AND entity_id = ?",
        (entity_type, entity_id),
    )
    conn.commit()
