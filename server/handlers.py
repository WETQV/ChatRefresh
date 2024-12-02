# server/handlers.py

import json
import logging
from auth import authenticate_user, register_user
from config import FILES_DIR, BUFFER_SIZE
import os
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

class ClientHandler:
    def __init__(self, conn, addr, server):
        self.conn = conn  # Сохраняем соединение с клиентом
        self.addr = addr  # Сохраняем адрес клиента
        self.server = server  # Сохраняем ссылку на сервер
        self.nickname = None  # Изначально никнейм клиента не установлен
        self.buffer = ""  # Буфер для хранения входящих данных
        self.lock = threading.Lock()  # Мьютекс для потокобезопасности
        self.files_being_received = {}  # Словарь для отслеживания получаемых файлов

    def handle(self):
        """Обрабатывает подключение клиента и его сообщения."""
        logger.info(f"Подключен клиент с адресом: {self.addr}")
        try:
            auth_data = self.receive_message()  # Получаем данные аутентификации
            if not auth_data:
                logger.info(f"Клиент {self.addr} отключился до аутентификации.")
                self.conn.close()  # Закрываем соединение, если данных нет
                return
            auth_msg = json.loads(auth_data)  # Декодируем данные аутентификации
            if auth_msg['type'] == 'login':
                self.handle_login(auth_msg)  # Обрабатываем вход в систему
            elif auth_msg['type'] == 'register':
                self.handle_register(auth_msg)  # Обрабатываем регистрацию
            else:
                self.send_response({'type': 'response', 'status': 'error', 'message': 'Неверный тип запроса'})
                self.conn.close()  # Закрываем соединение при неверном запросе
                return

            # После успешной аутентификации обрабатываем дальнейшие сообщения
            while True:
                data = self.receive_message()  # Получаем следующее сообщение
                if not data:
                    break  # Выходим из цикла, если данных нет
                msg = json.loads(data)  # Декодируем сообщение
                if msg['type'] == 'message':
                    self.handle_chat_message(msg)  # Обрабатываем сообщение чата
                elif msg['type'] == 'file':
                    self.handle_file_upload(msg)  # Обрабатываем загрузку файла
                elif msg['type'] == 'list_files':
                    self.handle_list_files()  # Обрабатываем запрос на список файлов
                elif msg['type'] == 'download_file':
                    self.handle_download_file(msg)  # Обрабатываем запрос на скачивание файла
                else:
                    self.send_response({'type': 'response', 'status': 'error', 'message': 'Неизвестный тип сообщения'})
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка с клиентом {self.addr}: {e}")  # Логируем ошибку декодирования JSON
        except Exception as e:
            logger.error(f"Ошибка с клиентом {self.addr}: {e}")  # Логируем общую ошибку
        finally:
            logger.info(f"Клиент {self.addr} отключен.")  # Логируем отключение клиента
            with self.server.clients_lock:
                if self.conn in self.server.clients:
                    del self.server.clients[self.conn]  # Удаляем клиента из списка
            self.conn.close()  # Закрываем соединение

    def receive_message(self):
        """Принимает одно полное сообщение, разделенное '\n'."""
        try:
            while True:
                data = self.conn.recv(self.server.BUFFER_SIZE).decode()  # Получаем данные от клиента
                if not data:
                    return None  # Возвращаем None, если данных нет
                self.buffer += data  # Добавляем данные в буфер
                if '\n' in self.buffer:
                    message, self.buffer = self.buffer.split('\n', 1)  # Разделяем сообщение по '\n'
                    return message.strip()  # Возвращаем очищенное сообщение
        except Exception as e:
            logger.error(f"Ошибка при приёме сообщения от {self.addr}: {e}")  # Логируем ошибку при приеме
            return None  # Возвращаем None в случае ошибки

    def send_response(self, message):
        """Отправляет сообщение клиенту, добавляя '\n' как разделитель."""
        try:
            self.conn.send((json.dumps(message) + '\n').encode())  # Отправляем сообщение клиенту
            logger.debug(f"Отправлено сообщение клиенту {self.addr}: {message}")  # Логируем отправленное сообщение
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения клиенту {self.addr}: {e}")  # Логируем ошибку отправки

    def handle_login(self, auth_msg):
        """Обрабатывает вход пользователя в систему."""
        nickname = auth_msg['nickname']  # Получаем никнейм
        password = auth_msg['password']  # Получаем пароль
        if authenticate_user(nickname, password):  # Проверяем учетные данные
            response = {'type': 'response', 'status': 'success', 'message': 'Успешный вход'}
            with self.server.clients_lock:
                self.server.clients[self.conn] = nickname  # Добавляем клиента в список
            self.nickname = nickname  # Сохраняем никнейм
            logger.info(f"Пользователь {nickname} вошел в систему.")  # Логируем успешный вход
        else:
            response = {'type': 'response', 'status': 'error', 'message': 'Неверные учетные данные'}
        self.send_response(response)  # Отправляем ответ клиенту
        if response['status'] != 'success':
            self.conn.close()  # Закрываем соединение при ошибке

    def handle_register(self, auth_msg):
        """Обрабатывает регистрацию нового пользователя."""
        nickname = auth_msg['nickname']  # Получаем никнейм
        password = auth_msg['password']  # Получаем пароль
        if register_user(nickname, password):  # Регистрируем пользователя
            response = {'type': 'response', 'status': 'success', 'message': 'Успешная регистрация'}
            with self.server.clients_lock:
                self.server.clients[self.conn] = nickname  # Добавляем клиента в список
            self.nickname = nickname  # Сохраняем никнейм
            logger.info(f"Пользователь {nickname} зарегистрирован.")  # Логируем успешную регистрацию
        else:
            response = {'type': 'response', 'status': 'error', 'message': 'Пользователь уже существует'}
        self.send_response(response)  # Отправляем ответ клиенту
        if response['status'] != 'success':
            self.conn.close()  # Закрываем соединение при ошибке

    def handle_chat_message(self, msg):
        """Обрабатывает сообщение чата от клиента."""
        content = msg['content']  # Получаем содержимое сообщения
        sender = self.nickname if self.nickname else 'Unknown'  # Определяем отправителя
        broadcast_msg = {'type': 'message', 'sender': sender, 'content': content}  # Формируем сообщение для рассылки
        self.server.broadcast(broadcast_msg, sender=sender)  # Рассылаем сообщение всем клиентам
        logger.info(f"Сообщение от {sender}: {content}")  # Логируем сообщение

    def handle_file_upload(self, msg):
        """Обрабатывает загрузку файла от клиента."""
        file_name = msg['file_name']  # Получаем имя файла
        file_size = msg.get('file_size', '0 Б')  # Получаем размер файла
        total_chunks = msg.get('total_chunks', 1)  # Получаем общее количество чанков
        current_chunk = msg.get('current_chunk', 1)  # Получаем номер текущего чанка
        file_data_hex = msg['file_data']  # Получаем данные файла в шестнадцатеричном формате
        sender = self.nickname if self.nickname else 'Unknown'  # Определяем отправителя
        date = msg.get('date', 'Unknown')  # Получаем дату

        logger.info(f"Получен файл {file_name} от {sender} (Чанк {current_chunk}/{total_chunks})")  # Логируем получение файла

        if file_name not in self.files_being_received:
            # Инициализируем запись нового файла
            safe_file_name = self.get_safe_filename(sender, file_name)  # Генерируем безопасное имя файла
            file_path = os.path.join(FILES_DIR, safe_file_name)  # Формируем полный путь к файлу
            self.files_being_received[file_name] = {
                'total_chunks': total_chunks,  # Сохраняем общее количество чанков
                'received_chunks': 0,  # Изначально получено 0 чанков
                'file_path': file_path,  # Сохраняем путь к файлу
                'file_size': file_size,  # Сохраняем размер файла
                'file_type': self.get_file_type(file_path),  # Определяем тип файла
                'sender': sender,  # Сохраняем отправителя
                'date': date  # Сохраняем дату
            }

        file_info = self.files_being_received[file_name]  # Получаем информацию о файле
        try:
            with self.lock:
                # Открываем файл в режиме добавления или создания
                mode = 'ab' if current_chunk > 1 else 'wb'  # Определяем режим открытия файла
                with open(file_info['file_path'], mode) as f:
                    f.write(bytes.fromhex(file_data_hex))  # Записываем данные в файл
            file_info['received_chunks'] += 1  # Увеличиваем счетчик полученных чанков
            logger.info(f"Чанк {current_chunk} файла {file_name} сохранен.")  # Логируем сохранение чанка

            if file_info['received_chunks'] == file_info['total_chunks']:
                logger.info(f"Файл {file_name} от {sender} полностью сохранен.")  # Логируем полное сохранение файла
                # Рассылка информации о новом файле всем клиентам
                new_file_msg = {
                    'type': 'new_file',  # Тип сообщения
                    'file_name': file_name,  # Имя файла
                    'file_size': file_info['file_size'],  # Размер файла
                    'file_type': file_info['file_type'],  # Тип файла
                    'sender': file_info['sender'],  # Отправитель
                    'date': file_info['date']  # Дата
                }
                self.server.broadcast(new_file_msg, sender=None)  # Отправить всем клиентам

                # Удаление информации о полученном файле
                del self.files_being_received[file_name]  # Удаляем информацию о файле
        except Exception as e:
            logger.error(f"Ошибка при сохранении чанка файла {file_name}: {e}")  # Логируем ошибку сохранения
            self.send_response({'type': 'response', 'status': 'error', 'message': f'Ошибка при сохранении файла {file_name}'})  # Отправляем сообщение об ошибке
            del self.files_being_received[file_name]  # Удаляем информацию о файле

    def handle_list_files(self):
        """Обрабатывает запрос клиента на список файлов."""
        try:
            files = self.get_files_list()  # Получаем список файлов
            response = {'type': 'files_list', 'files': files}  # Формируем ответ
            self.send_response(response)  # Отправляем ответ клиенту
            logger.info(f"Отправлен список файлов клиенту {self.addr}")  # Логируем отправку списка файлов
        except Exception as e:
            logger.error(f"Ошибка при отправке списка файлов клиенту {self.addr}: {e}")  # Логируем ошибку отправки
            self.send_response({'type': 'response', 'status': 'error', 'message': 'Не удалось получить список файлов'})  # Отправляем сообщение об ошибке

    def handle_download_file(self, msg):
        """Обрабатывает запрос клиента на скачивание файла."""
        file_name = msg['file_name']  # Получаем имя файла
        safe_file_name = self.get_safe_filename_from_server(file_name)  # Получаем безопасное имя файла
        file_path = os.path.join(FILES_DIR, safe_file_name)  # Формируем полный путь к файлу

        if not os.path.exists(file_path):
            self.send_response({'type': 'response', 'status': 'error', 'message': f'Файл {file_name} не найден на сервере'})  # Отправляем сообщение об ошибке
            logger.warning(f"Файл {file_name} не найден для скачивания клиентом {self.addr}")  # Логируем предупреждение
            return

        # Получение информации о файле
        file_size_bytes = os.path.getsize(file_path)  # Получаем размер файла в байтах
        total_chunks = (file_size_bytes // BUFFER_SIZE) + (1 if file_size_bytes % BUFFER_SIZE != 0 else 0)  # Вычисляем общее количество чанков

        # Отправка информации о файле
        file_info = {
            'type': 'file_info',  # Тип сообщения
            'file_name': file_name,  # Имя файла
            'file_size': self.get_readable_file_size(file_size_bytes),  # Читаемый размер файла
            'file_type': self.get_file_type(file_path),  # Тип файла
            'total_chunks': total_chunks,  # Общее количество чанков
            'sender': 'Server',  # Отправитель
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Текущая дата и время
        }
        self.send_response(file_info)  # Отправляем информацию о файле

        # Отправка файла в чанках
        try:
            with open(file_path, 'rb') as f:
                chunk_number = 1  # Номер чанка
                while True:
                    file_data = f.read(BUFFER_SIZE)  # Читаем данные чанка
                    if not file_data:
                        break  # Выходим из цикла, если данных нет
                    file_data_hex = file_data.hex()  # Преобразуем данные в шестнадцатеричный формат
                    chunk_msg = {
                        'type': 'file_chunk',  # Тип сообщения
                        'file_name': file_name,  # Имя файла
                        'chunk_number': chunk_number,  # Номер чанка
                        'total_chunks': total_chunks,  # Общее количество чанков
                        'file_data': file_data_hex  # Данные чанка
                    }
                    self.send_response(chunk_msg)  # Отправляем чанк клиенту
                    logger.info(f"Отправлен файл {file_name} Чанк {chunk_number}/{total_chunks} клиенту {self.addr}")  # Логируем отправку чанка
                    chunk_number += 1  # Увеличиваем номер чанка
            # Завершение отправки файла
            self.send_response({'type': 'file_complete', 'file_name': file_name})  # Отправляем сообщение о завершении
            logger.info(f"Файл {file_name} полностью отправлен клиенту {self.addr}")  # Логируем завершение отправки
        except Exception as e:
            logger.error(f"Ошибка при отправке файла {file_name} клиенту {self.addr}: {e}")  # Логируем ошибку отправки
            self.send_response({'type': 'response', 'status': 'error', 'message': f'Ошибка при отправке файла {file_name}'})  # Отправляем сообщение об ошибке

    def get_safe_filename(self, sender, file_name):
        """Генерирует безопасное имя файла, избегая конфликтов."""
        # Можно добавить проверку на безопасность, убрать опасные символы и т.д.
        # Здесь просто добавим префикс с ником отправителя
        safe_name = f"{sender}_{file_name}"  # Формируем безопасное имя файла
        return safe_name  # Возвращаем безопасное имя

    def get_safe_filename_from_server(self, file_name):
        """Получает безопасное имя файла на сервере."""
        # Предполагается, что файлы на сервере хранятся как {sender}_{file_name}
        # Если известно имя отправителя, можно искать соответствующий файл
        # Для простоты, если несколько файлов с одинаковыми именами, это может вызвать проблемы
        # Здесь предполагаем, что имена уникальны
        for f in os.listdir(FILES_DIR):
            if f.endswith(f"_{file_name}"):  # Проверяем, заканчивается ли имя файла на нужное
                return f  # Возвращаем найденное имя
        # Если файл не найден, вернуть оригинальное имя
        return file_name  # Возвращаем оригинальное имя, если ничего не найдено

    def get_files_list(self):
        """Возвращает список файлов на сервере с метаданными."""
        files = []  # Список для хранения информации о файлах
        for f in os.listdir(FILES_DIR):  # Проходим по всем файлам в директории
            file_path = os.path.join(FILES_DIR, f)  # Формируем полный путь к файлу
            if os.path.isfile(file_path):  # Проверяем, является ли это файлом
                file_size_bytes = os.path.getsize(file_path)  # Получаем размер файла в байтах
                file_size = self.get_readable_file_size(file_size_bytes)  # Получаем читаемый размер файла
                file_type = self.get_file_type(file_path)  # Определяем тип файла
                # Получение даты создания или модификации
                mod_time = os.path.getmtime(file_path)  # Получаем время последней модификации
                date = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")  # Форматируем дату
                # Получатель файла из имени, предположим формат: {sender}_{file_name}
                parts = f.split('_', 1)  # Разделяем имя файла на части
                sender = parts[0] if len(parts) > 1 else 'Unknown'  # Получаем отправителя
                original_file_name = parts[1] if len(parts) > 1 else f  # Получаем оригинальное имя файла
                files.append({
                    'file_name': original_file_name,  # Оригинальное имя файла
                    'file_size': file_size,  # Читаемый размер файла
                    'file_type': file_type,  # Тип файла
                    'sender': sender,  # Отправитель
                    'date': date  # Дата
                })
        return files  # Возвращаем список файлов

    def get_readable_file_size(self, size_in_bytes):
        """Преобразует размер файла из байт в читаемый формат."""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:  # Перебираем единицы измерения
            if size_in_bytes < 1024:  # Если размер меньше 1024
                return f"{size_in_bytes} {unit}"  # Возвращаем размер с единицей измерения
            size_in_bytes /= 1024  # Делим на 1024 для перехода к следующей единице
        return f"{size_in_bytes:.2f} ПБ"  # Возвращаем размер в ПБ

    def get_file_type(self, file_path):
        """Определяет тип файла по расширению."""
        _, ext = os.path.splitext(file_path)  # Получаем расширение файла
        ext = ext.lower()  # Приводим к нижнему регистру
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            return 'Изображение'  # Возвращаем тип 'Изображение'
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
            return 'Видео'  # Возвращаем тип 'Видео'
        elif ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.txt']:
            return 'Документ'  # Возвращаем тип 'Документ'
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return 'Архив'  # Возвращаем тип 'Архив'
        elif ext in ['.mp3', '.wav', '.aac', '.flac']:
            return 'Музыка'  # Возвращаем тип 'Музыка'
        else:
            return 'Другой'  # Возвращаем тип 'Другой'