# server/database.py

import sqlite3
import logging
from config import USERS_DB

logger = logging.getLogger(__name__)

def init_db():
    try:
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована.")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")

def get_user_password_hash(nickname):
    try:
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE nickname = ?', (nickname,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении хэша пароля для {nickname}: {e}")
        return None

def add_user(nickname, password_hash):
    try:
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (nickname, password_hash) VALUES (?, ?)', (nickname, password_hash))
        conn.commit()
        conn.close()
        logger.info(f"Пользователь {nickname} добавлен в базу данных.")
    except sqlite3.IntegrityError:
        logger.warning(f"Попытка добавить существующего пользователя: {nickname}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {nickname}: {e}")
        raise