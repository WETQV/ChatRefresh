# server/server.py

import socket
import threading
import os
import json
import logging
from config import (TCP_PORT, UDP_PORT, BUFFER_SIZE, FILES_DIR, 
                   ENABLE_DIRECTORY_REGISTRATION, DIRECTORY_SERVER_IP, 
                   DIRECTORY_SERVER_PORT, USE_UPNP,
                   SMALL_FILE_THRESHOLD, MEDIUM_FILE_THRESHOLD,
                   LARGE_FILE_THRESHOLD, SMALL_FILE_BUFFER,
                   MEDIUM_FILE_BUFFER, LARGE_FILE_BUFFER, HUGE_FILE_BUFFER)
from database import init_db
from handlers import ClientHandler
from utils import get_server_ip

# Настройка логирования с поддержкой UTF-8
logging.basicConfig(
    level=logging.INFO,  # Можно изменить на DEBUG для более подробных логов
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("server.log", encoding='utf-8'),  # Указана кодировка utf-8
        logging.StreamHandler()
    ]
)

# Получаем логгер для текущего модуля
logger = logging.getLogger(__name__)

class ChatServer:
    def __init__(self, tcp_port, udp_port):
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.clients = {}  # conn: nickname
        self.clients_lock = threading.Lock()
        self.BUFFER_SIZE = BUFFER_SIZE
        self.init_environment()
        if ENABLE_DIRECTORY_REGISTRATION:
            self.register_with_directory()
        logger.info("ChatServer инициализирован.")

    def init_environment(self):
        # Создание директории для хранения файлов, если она не существует
        if not os.path.exists(FILES_DIR):
            os.makedirs(FILES_DIR)
            logger.info(f"Создана директория для файлов: {FILES_DIR}")
        else:
            logger.info(f"Директория для файлов уже существует: {FILES_DIR}")
        # Инициализация базы данных
        init_db()
        logger.info("Инициализация базы данных завершена.")

    def udp_broadcast_listener(self):
        """Слушает UDP-запросы на обнаружение сервера."""
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind(('', self.udp_port))
        logger.info(f"UDP-обнаружение запущено на порту {self.udp_port}")

        while True:
            try:
                data, addr = udp_socket.recvfrom(1024)
                logger.info(f"Получен UDP-запрос от {addr}: {data.decode().strip()}")
                if data.decode().strip() == 'DISCOVER_SERVER':
                    server_ip = get_server_ip(addr[0])
                    response = f'SERVER_IP:{server_ip};TCP_PORT:{self.tcp_port}\n'
                    udp_socket.sendto(response.encode(), addr)
                    logger.info(f"Отправлен ответ: {response.strip()} клиенту {addr}")
            except Exception as e:
                logger.error(f"Ошибка в UDP-слушателе: {e}")

    def handle_client_connection(self, conn, addr):
        logger.info(f"Начата обработка клиента {addr}")
        handler = ClientHandler(conn, addr, self)
        handler_thread = threading.Thread(target=handler.handle, daemon=True)
        handler_thread.start()

    def broadcast(self, message, sender=None):
        """Отправляет сообщение всем подключенным клиентам, кроме отправителя."""
        with self.clients_lock:
            for client_conn, nickname in list(self.clients.items()):
                if nickname != sender:
                    try:
                        client_conn.send((json.dumps(message) + '\n').encode())
                        logger.info(f"Отправлено сообщение клиенту {nickname}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке сообщения клиенту {nickname}: {e}")
                        client_conn.close()
                        del self.clients[client_conn]

    def register_with_directory(self):
        """Регистрирует сервер в централизованном справочнике."""
        # Поскольку вы не используете справочник, этот метод может быть отключен или удалён
        logger.info("Регистрация в справочном сервере отключена.")

    def start_server(self):
        """Запускает сервер."""
        # Запускаем поток для UDP-обнаружения
        udp_thread = threading.Thread(target=self.udp_broadcast_listener, daemon=True)
        udp_thread.start()
        logger.info("Поток UDP-обнаружения запущен.")

        # Настраиваем TCP-сервер
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.bind(('0.0.0.0', self.tcp_port))
            tcp_socket.listen()
            logger.info(f"TCP-сервер запущен на порту {self.tcp_port}")
        except Exception as e:
            logger.critical(f"Не удалось запустить TCP-сервер: {e}")
            return

        while True:
            try:
                conn, addr = tcp_socket.accept()
                logger.info(f"Подключение от {addr}")
                self.handle_client_connection(conn, addr)
            except Exception as e:
                logger.error(f"Ошибка при принятии подключения: {e}")

if __name__ == "__main__":
    server = ChatServer(tcp_port=TCP_PORT, udp_port=UDP_PORT)
    server.start_server()