# server/auth.py

import bcrypt
import sqlite3
import logging
from database import get_user_password_hash, add_user

logger = logging.getLogger(__name__)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def authenticate_user(nickname, password):
    stored_hash = get_user_password_hash(nickname)
    if stored_hash:
        result = check_password(password, stored_hash)
        logger.info(f"Аутентификация пользователя {nickname}: {'успешно' if result else 'неудачно'}")
        return result
    logger.warning(f"Попытка аутентификации несуществующего пользователя: {nickname}")
    return False

def register_user(nickname, password):
    try:
        password_hash = hash_password(password)
        add_user(nickname, password_hash)
        logger.info(f"Пользователь {nickname} зарегистрирован.")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Попытка регистрации существующего пользователя: {nickname}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя {nickname}: {e}")
        return False