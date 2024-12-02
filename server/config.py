# server/config.py

import os

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Получаем абсолютный путь к директории текущего файла
USERS_DB = os.path.join(BASE_DIR, 'users.db')  # Формируем путь к базе данных пользователей
FILES_DIR = os.path.join(BASE_DIR, 'uploaded_files')  # Формируем путь к директории для загруженных файлов

# Порты
TCP_PORT = 12345  # Устанавливаем TCP порт для сервера
UDP_PORT = 37020  # Устанавливаем UDP порт для сервера

# Размер буфера
BUFFER_SIZE = 4096  # Устанавливаем размер буфера для передачи данных

# Конфигурация Централизованного Справочника
ENABLE_DIRECTORY_REGISTRATION = False  # Включаем или отключаем регистрацию в справочнике
DIRECTORY_SERVER_IP = 'your.directory.server.ip'  # Указываем IP адрес централизованного справочника
DIRECTORY_SERVER_PORT = 50000  # Указываем порт, на котором работает справочник

# Конфигурация UPnP
USE_UPNP = False  # Включаем или отключаем поддержку UPnP