# server/database.py

import sqlite3
import logging
from config import USERS_DB

logger = logging.getLogger(__name__)

def init_db():
    # Инициализирует базу данных, создавая таблицу пользователей, если она не существует
    try:
        conn = sqlite3.connect(USERS_DB)  # Подключение к базе данных
        cursor = conn.cursor()  # Создание курсора для выполнения SQL-запросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL 
            )
        ''')
        conn.commit()  # Сохранение изменений
        conn.close()  # Закрытие соединения с базой данных
        logger.info("База данных инициализирована.")  # Логирование успешной инициализации
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")  # Логирование ошибки

def get_user_password_hash(nickname):
    # Получает хеш пароля пользователя по его никнейму
    try:
        conn = sqlite3.connect(USERS_DB)  # Подключение к базе данных
        cursor = conn.cursor()  # Создание курсора
        cursor.execute('SELECT password_hash FROM users WHERE nickname = ?', (nickname,))  # Выполнение запроса
        row = cursor.fetchone()  # Получение результата запроса
        conn.close()  # Закрытие соединения
        if row:
            return row[0]  # Возвращает хеш пароля, если пользователь найден
        return None  # Возвращает None, если пользователь не найден
    except Exception as e:
        logger.error(f"Ошибка при получении хэша пароля для {nickname}: {e}")  # Логирование ошибки
        return None  # Возвращает None в случае ошибки

def add_user(nickname, password_hash):
    # Добавляет нового пользователя в базу данных
    try:
        conn = sqlite3.connect(USERS_DB)  # Подключение к базе данных
        cursor = conn.cursor()  # Создание курсора
        cursor.execute('INSERT INTO users (nickname, password_hash) VALUES (?, ?)', (nickname, password_hash))  # Вставка данных
        conn.commit()  # Сохранение изменений
        conn.close()  # Закрытие соединения
        logger.info(f"Пользователь {nickname} добавлен в базу данных.")  # Логирование успешного добавления
    except sqlite3.IntegrityError:
        logger.warning(f"Попытка добавить существующего пользователя: {nickname}")  # Логирование попытки добавить существующего пользователя
        raise  # Генерация исключения
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {nickname}: {e}")  # Логирование ошибки
        raise  # Генерация исключения