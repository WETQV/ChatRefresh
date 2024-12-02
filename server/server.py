# server/server.py

import socket
import threading
import os
import json
import logging
from config import TCP_PORT, UDP_PORT, BUFFER_SIZE, FILES_DIR, ENABLE_DIRECTORY_REGISTRATION, DIRECTORY_SERVER_IP, DIRECTORY_SERVER_PORT, USE_UPNP
from database import init_db
from handlers import ClientHandler
from utils import get_server_ip

# Настройка логирования с поддержкой UTF-8
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования, можно изменить на DEBUG для более подробных логов
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("server.log", encoding='utf-8'),  # Логирование в файл с кодировкой utf-8
        logging.StreamHandler()  # Логирование в поток (консоль)
    ]
)

# Получаем логгер для текущего модуля
logger = logging.getLogger(__name__)

class ChatServer:
    def __init__(self, tcp_port, udp_port):
        self.tcp_port = tcp_port  # Устанавливаем TCP порт
        self.udp_port = udp_port  # Устанавливаем UDP порт
        self.clients = {}  # Словарь для хранения клиентов (соединение: никнейм)
        self.clients_lock = threading.Lock()  # Мьютекс для потокобезопасности
        self.BUFFER_SIZE = BUFFER_SIZE  # Размер буфера для передачи данных
        self.init_environment()  # Инициализация окружения сервера
        if ENABLE_DIRECTORY_REGISTRATION:
            self.register_with_directory()  # Регистрация в справочнике, если включена
        logger.info("ChatServer инициализирован.")  # Логируем инициализацию сервера

    def init_environment(self):
        # Создание директории для хранения файлов, если она не существует
        if not os.path.exists(FILES_DIR):
            os.makedirs(FILES_DIR)  # Создаем директорию
            logger.info(f"Создана директория для файлов: {FILES_DIR}")  # Логируем создание директории
        else:
            logger.info(f"Директория для файлов уже существует: {FILES_DIR}")  # Логируем, если директория уже существует
        # Инициализация базы данных
        init_db()  # Вызываем функцию инициализации базы данных
        logger.info("Инициализация базы данных завершена.")  # Логируем завершение инициализации базы данных

    def udp_broadcast_listener(self):
        """Слушает UDP-запросы на обнаружение сервера."""
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Создаем UDP сокет
        udp_socket.bind(('', self.udp_port))  # Привязываем сокет к порту
        logger.info(f"UDP-обнаружение запущено на порту {self.udp_port}")  # Логируем запуск UDP-обнаружения

        while True:
            try:
                data, addr = udp_socket.recvfrom(1024)  # Получаем данные от клиента
                logger.info(f"Получен UDP-запрос от {addr}: {data.decode().strip()}")  # Логируем полученный запрос
                if data.decode().strip() == 'DISCOVER_SERVER':  # Проверяем, является ли запрос запросом на обнаружение
                    server_ip = get_server_ip(addr[0])  # Получаем IP сервера
                    response = f'SERVER_IP:{server_ip};TCP_PORT:{self.tcp_port}\n'  # Формируем ответ
                    udp_socket.sendto(response.encode(), addr)  # Отправляем ответ клиенту
                    logger.info(f"Отправлен ответ: {response.strip()} клиенту {addr}")  # Логируем отправленный ответ
            except Exception as e:
                logger.error(f"Ошибка в UDP-слушателе: {e}")  # Логируем ошибку в UDP-слушателе

    def handle_client_connection(self, conn, addr):
        logger.info(f"Начата обработка клиента {addr}")  # Логируем начало обработки клиента
        handler = ClientHandler(conn, addr, self)  # Создаем обработчик клиента
        handler_thread = threading.Thread(target=handler.handle, daemon=True)  # Создаем поток для обработки клиента
        handler_thread.start()  # Запускаем поток

    def broadcast(self, message, sender=None):
        """Отправляет сообщение всем подключенным клиентам, кроме отправителя."""
        with self.clients_lock:  # Блокируем доступ к списку клиентов
            for client_conn, nickname in list(self.clients.items()):  # Проходим по всем клиентам
                if nickname != sender:  # Если клиент не отправитель
                    try:
                        client_conn.send((json.dumps(message) + '\n').encode())  # Отправляем сообщение клиенту
                        logger.info(f"Отправлено сообщение клиенту {nickname}")  # Логируем отправку сообщения
                    except Exception as e:
                        logger.error(f"Ошибка при отправке сообщения клиенту {nickname}: {e}")  # Логируем ошибку отправки
                        client_conn.close()  # Закрываем соединение с клиентом
                        del self.clients[client_conn]  # Удаляем клиента из списка

    def register_with_directory(self):
        """Регистрирует сервер в централизованном справочнике."""
        # Поскольку вы не используете справочник, этот метод может быть отключен или удалён
        logger.info("Регистрация в справочном сервере отключена.")  # Логируем отключение регистрации

    def start_server(self):
        """Запускает сервер."""
        # Запускаем поток для UDP-обнаружения
        udp_thread = threading.Thread(target=self.udp_broadcast_listener, daemon=True)  # Создаем поток для UDP-обнаружения
        udp_thread.start()  # Запускаем поток
        logger.info("Поток UDP-обнаружения запущен.")  # Логируем запуск потока

        # Настраиваем TCP-сервер
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Создаем TCP сокет
            tcp_socket.bind(('0.0.0.0', self.tcp_port))  # Привязываем сокет к порту
            tcp_socket.listen()  # Начинаем прослушивание входящих соединений
            logger.info(f"TCP-сервер запущен на порту {self.tcp_port}")  # Логируем запуск TCP-сервера
        except Exception as e:
            logger.critical(f"Не удалось запустить TCP-сервер: {e}")  # Логируем критическую ошибку
            return  # Выходим из метода

        while True:
            try:
                conn, addr = tcp_socket.accept()  # Принимаем входящее соединение
                logger.info(f"Подключение от {addr}")  # Логируем подключение клиента
                self.handle_client_connection(conn, addr)  # Обрабатываем подключение клиента
            except Exception as e:
                logger.error(f"Ошибка при принятии подключения: {e}")  # Логируем ошибку при принятии подключения

if __name__ == "__main__":
    server = ChatServer(tcp_port=TCP_PORT, udp_port=UDP_PORT)  # Создаем экземпляр сервера
    server.start_server()  # Запускаем сервер