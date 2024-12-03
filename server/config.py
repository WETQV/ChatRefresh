# server/config.py

import os

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DB = os.path.join(BASE_DIR, 'users.db')
FILES_DIR = os.path.join(BASE_DIR, 'uploaded_files')

# Порты
TCP_PORT = 12345
UDP_PORT = 37020

# Размеры буфера для разных размеров файлов
BUFFER_SIZE = 4096  # Базовый размер буфера для обычных операций
SMALL_FILE_THRESHOLD = 1024 * 1024  # 1 MB
MEDIUM_FILE_THRESHOLD = 10 * 1024 * 1024  # 10 MB
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100 MB

SMALL_FILE_BUFFER = 512 * 1024  # 512 KB для файлов < 1 MB
MEDIUM_FILE_BUFFER = 1024 * 1024  # 1 MB для файлов от 1 MB до 10 MB
LARGE_FILE_BUFFER = 2 * 1024 * 1024  # 2 MB для файлов от 10 MB до 100 MB
HUGE_FILE_BUFFER = 4 * 1024 * 1024  # 4 MB для файлов > 100 MB

# Конфигурация Централизованного Справочника
ENABLE_DIRECTORY_REGISTRATION = False  # Включить/Отключить регистрацию в справочнике
DIRECTORY_SERVER_IP = 'your.directory.server.ip'  # Замените на IP вашего справочника
DIRECTORY_SERVER_PORT = 50000  # Порт, на котором работает справочник

# Конфигурация UPnP
USE_UPNP = False  # Включить/Отключить UPnP