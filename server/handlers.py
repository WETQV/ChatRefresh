# server/handlers.py

import json
import logging
from auth import authenticate_user, register_user
from config import (FILES_DIR, BUFFER_SIZE, SMALL_FILE_THRESHOLD, MEDIUM_FILE_THRESHOLD, 
                   LARGE_FILE_THRESHOLD, SMALL_FILE_BUFFER, MEDIUM_FILE_BUFFER, 
                   LARGE_FILE_BUFFER, HUGE_FILE_BUFFER)
import os
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

class ClientHandler:
    def __init__(self, conn, addr, server):
        self.conn = conn
        self.addr = addr
        self.server = server
        self.nickname = None
        self.buffer = ""
        self.lock = threading.Lock()
        self.files_being_received = {}  # file_name: {'total_chunks': int, 'received_chunks': int, 'file_path': str}
    
    def handle(self):
        logger.info(f"Подключен клиент с адресом: {self.addr}")
        try:
            auth_data = self.receive_message()
            if not auth_data:
                logger.info(f"Клиент {self.addr} отключился до аутентификации.")
                self.conn.close()
                return
            auth_msg = json.loads(auth_data)
            if auth_msg['type'] == 'login':
                self.handle_login(auth_msg)
            elif auth_msg['type'] == 'register':
                self.handle_register(auth_msg)
            else:
                self.send_response({'type': 'response', 'status': 'error', 'message': 'Неверный тип запроса'})
                self.conn.close()
                return

            # После успешной аутентификации обрабатываем дальнейшие сообщения
            while True:
                data = self.receive_message()
                if not data:
                    break
                msg = json.loads(data)
                if msg['type'] == 'message':
                    self.handle_chat_message(msg)
                elif msg['type'] == 'file':
                    self.handle_file_upload(msg)
                elif msg['type'] == 'list_files':
                    self.handle_list_files()
                elif msg['type'] == 'download_file':
                    self.handle_download_file(msg)
                else:
                    self.send_response({'type': 'response', 'status': 'error', 'message': 'Неизвестный тип сообщения'})
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка с клиентом {self.addr}: {e}")
        except Exception as e:
            logger.error(f"Ошибка с клиентом {self.addr}: {e}")
        finally:
            logger.info(f"Клиент {self.addr} отключен.")
            with self.server.clients_lock:
                if self.conn in self.server.clients:
                    del self.server.clients[self.conn]
            self.conn.close()

    def receive_message(self):
        """Принимает одно полное сообщение, разделенное '\n'."""
        try:
            while True:
                data = self.conn.recv(self.server.BUFFER_SIZE).decode()
                if not data:
                    return None
                self.buffer += data
                if '\n' in self.buffer:
                    message, self.buffer = self.buffer.split('\n', 1)
                    return message.strip()
        except Exception as e:
            logger.error(f"Ошибка при приёме сообщения от {self.addr}: {e}")
            return None

    def send_response(self, message):
        """Отправляет сообщение клиенту, добавляя '\n' как разделитель."""
        try:
            self.conn.send((json.dumps(message) + '\n').encode())
            logger.debug(f"Отправлено сообщение клиенту {self.addr}: {message}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения клиенту {self.addr}: {e}")

    def handle_login(self, auth_msg):
        nickname = auth_msg['nickname']
        password = auth_msg['password']
        if authenticate_user(nickname, password):
            response = {'type': 'response', 'status': 'success', 'message': 'Успешный вход'}
            with self.server.clients_lock:
                self.server.clients[self.conn] = nickname
            self.nickname = nickname
            logger.info(f"Пользователь {nickname} вошел в систему.")
        else:
            response = {'type': 'response', 'status': 'error', 'message': 'Неверные учетные данные'}
        self.send_response(response)
        if response['status'] != 'success':
            self.conn.close()

    def handle_register(self, auth_msg):
        nickname = auth_msg['nickname']
        password = auth_msg['password']
        if register_user(nickname, password):
            response = {'type': 'response', 'status': 'success', 'message': 'Успешная регистрация'}
            with self.server.clients_lock:
                self.server.clients[self.conn] = nickname
            self.nickname = nickname
            logger.info(f"Пользователь {nickname} зарегистрирован.")
        else:
            response = {'type': 'response', 'status': 'error', 'message': 'Пользователь уже существует'}
        self.send_response(response)
        if response['status'] != 'success':
            self.conn.close()

    def handle_chat_message(self, msg):
        content = msg['content']
        sender = self.nickname if self.nickname else 'Unknown'
        broadcast_msg = {'type': 'message', 'sender': sender, 'content': content}
        self.server.broadcast(broadcast_msg, sender=sender)
        logger.info(f"Сообщение от {sender}: {content}")

    def handle_file_upload(self, msg):
        """Обрабатывает загрузку файла от клиента."""
        file_name = msg['file_name']
        file_size = msg.get('file_size', '0 Б')  # Размер файла
        total_chunks = msg.get('total_chunks', 1)
        current_chunk = msg.get('current_chunk', 1)
        file_data_hex = msg['file_data']
        sender = self.nickname if self.nickname else 'Unknown'
        date = msg.get('date', 'Unknown')

        logger.info(f"Получен файл {file_name} от {sender} (Чанк {current_chunk}/{total_chunks})")

        if file_name not in self.files_being_received:
            # Инициализируем запись нового файла
            safe_file_name = self.get_safe_filename(sender, file_name)
            file_path = os.path.join(FILES_DIR, safe_file_name)
            self.files_being_received[file_name] = {
                'total_chunks': total_chunks,
                'received_chunks': 0,
                'file_path': file_path,
                'file_size': file_size,
                'file_type': self.get_file_type(file_path),
                'sender': sender,
                'date': date
            }

        file_info = self.files_being_received[file_name]
        try:
            with self.lock:
                # Открываем файл в режиме добавления или создания
                mode = 'ab' if current_chunk > 1 else 'wb'
                with open(file_info['file_path'], mode) as f:
                    f.write(bytes.fromhex(file_data_hex))
            file_info['received_chunks'] += 1
            logger.info(f"Чанк {current_chunk} файла {file_name} сохранен.")

            if file_info['received_chunks'] == file_info['total_chunks']:
                logger.info(f"Файл {file_name} от {sender} полностью сохранен.")
                # Рассылка информации о новом файле всем клиентам
                new_file_msg = {
                    'type': 'new_file',
                    'file_name': file_name,
                    'file_size': file_info['file_size'],
                    'file_type': file_info['file_type'],
                    'sender': file_info['sender'],
                    'date': file_info['date']
                }
                self.server.broadcast(new_file_msg, sender=None)  # Отправить всем клиентам

                # Удаление информации о полученном файле
                del self.files_being_received[file_name]
        except Exception as e:
            logger.error(f"Ошибка при сохранении чанка файла {file_name}: {e}")
            self.send_response({'type': 'response', 'status': 'error', 'message': f'Ошибка при сохранении файла {file_name}'})
            del self.files_being_received[file_name]

    def handle_list_files(self):
        """Обрабатывает запрос клиента на список файлов."""
        try:
            files = self.get_files_list()
            response = {'type': 'files_list', 'files': files}
            self.send_response(response)
            logger.info(f"Отправлен список файлов клиенту {self.addr}")
        except Exception as e:
            logger.error(f"Ошибка при отправке списка файлов клиенту {self.addr}: {e}")
            self.send_response({'type': 'response', 'status': 'error', 'message': 'Не удалось получить список файлов'})

    def handle_download_file(self, msg):
        """Обрабатывает запрос клиента на скачивание файла."""
        file_name = msg['file_name']
        safe_file_name = self.get_safe_filename_from_server(file_name)
        file_path = os.path.join(FILES_DIR, safe_file_name)

        if not os.path.exists(file_path):
            self.send_response({'type': 'response', 'status': 'error', 'message': f'Файл {file_name} не найден на сервере'})
            logger.warning(f"Файл {file_name} не найден для скачивания клиентом {self.addr}")
            return

        # Получение информации о файле
        file_size_bytes = os.path.getsize(file_path)
        buffer_size = self.get_buffer_size(file_size_bytes)
        total_chunks = (file_size_bytes // buffer_size) + (1 if file_size_bytes % buffer_size != 0 else 0)

        # Отправка информации о файле
        file_info = {
            'type': 'file_info',
            'file_name': file_name,
            'file_size': self.get_readable_file_size(file_size_bytes),
            'file_type': self.get_file_type(file_path),
            'total_chunks': total_chunks,
            'sender': 'Server',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.send_response(file_info)

        # Отправка файла в чанках
        try:
            with open(file_path, 'rb') as f:
                chunk_number = 1
                while True:
                    file_data = f.read(buffer_size)
                    if not file_data:
                        break
                    file_data_hex = file_data.hex()
                    chunk_msg = {
                        'type': 'file_chunk',
                        'file_name': file_name,
                        'chunk_number': chunk_number,
                        'total_chunks': total_chunks,
                        'file_data': file_data_hex
                    }
                    self.send_response(chunk_msg)
                    logger.info(f"Отправлен файл {file_name} Чанк {chunk_number}/{total_chunks} клиенту {self.addr}")
                    chunk_number += 1
            # Завершение отправки файла
            self.send_response({'type': 'file_complete', 'file_name': file_name})
            logger.info(f"Файл {file_name} полностью отправлен клиенту {self.addr}")
        except Exception as e:
            logger.error(f"Ошибка при отправке файла {file_name} клиенту {self.addr}: {e}")
            self.send_response({'type': 'response', 'status': 'error', 'message': f'Ошибка при отправке файла {file_name}'})

    def get_buffer_size(self, file_size):
        """Определяет оптимальный размер буфера в зависимости от размера файла."""
        if file_size < SMALL_FILE_THRESHOLD:
            return SMALL_FILE_BUFFER
        elif file_size < MEDIUM_FILE_THRESHOLD:
            return MEDIUM_FILE_BUFFER
        elif file_size < LARGE_FILE_THRESHOLD:
            return LARGE_FILE_BUFFER
        else:
            return HUGE_FILE_BUFFER

    def get_safe_filename(self, sender, file_name):
        """Генерирует безопасное имя файла, избегая конфликтов."""
        # Можно добавить проверку на безопасность, убрать опасные символы и т.д.
        # Здесь просто добавим префикс с ником отправителя
        safe_name = f"{sender}_{file_name}"
        return safe_name

    def get_safe_filename_from_server(self, file_name):
        """Получает безопасное имя файла на сервере."""
        # Предполагается, что файлы на сервере хранятся как {sender}_{file_name}
        # Если известно имя отправителя, можно искать соответствующий файл
        # Для простоты, если несколько файлов с одинаковыми именами, это может вызвать проблемы
        # Здесь предполагаем, что имена уникальны
        for f in os.listdir(FILES_DIR):
            if f.endswith(f"_{file_name}"):
                return f
        # Если файл не найден, вернуть оригинальное имя
        return file_name

    def get_files_list(self):
        """Возвращает список файлов на сервере с метаданными."""
        files = []
        for f in os.listdir(FILES_DIR):
            file_path = os.path.join(FILES_DIR, f)
            if os.path.isfile(file_path):
                file_size_bytes = os.path.getsize(file_path)
                file_size = self.get_readable_file_size(file_size_bytes)
                file_type = self.get_file_type(file_path)
                # Получение даты создания или модификации
                mod_time = os.path.getmtime(file_path)
                date = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                # Получатель файла из имени, предположим формат: {sender}_{file_name}
                parts = f.split('_', 1)
                sender = parts[0] if len(parts) > 1 else 'Unknown'
                original_file_name = parts[1] if len(parts) > 1 else f
                files.append({
                    'file_name': original_file_name,
                    'file_size': file_size,
                    'file_type': file_type,
                    'sender': sender,
                    'date': date
                })
        return files

    def get_readable_file_size(self, size_in_bytes):
        """Преобразует размер файла из байт в читаемый формат."""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}".rstrip('0').rstrip('.')  # Убираем лишние нули после точки
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} ПБ".rstrip('0').rstrip('.')  # Убираем лишние нули после точки

    def get_file_type(self, file_path):
        """Определяет тип файла по расширению."""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            return 'Изображение'
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
            return 'Видео'
        elif ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.txt']:
            return 'Документ'
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return 'Архив'
        elif ext in ['.mp3', '.wav', '.aac', '.flac']:
            return 'Музыка'
        else:
            return 'Другой'