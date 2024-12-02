# client.py
import socket
import threading
import json
import customtkinter as ctk
from tkinter import messagebox, filedialog, scrolledtext, ttk
import tkinter as tk
import os
from customtkinter import CTkTextbox
from PIL import Image, ImageTk
from datetime import datetime

# Настройки customtkinter
ctk.set_appearance_mode("System")  # Устанавливает режим отображения (светлый/темный)
ctk.set_default_color_theme("green")  # Устанавливает стандартную тему "green"

# Определяем цвета в одном месте для удобства изменения
COLORS = {
    'app_bg': "#A44E29",             # Цвет фона приложения
    'card_bg': "#BD6843",            # Цвет карточки (формы)
    'entry_bg': "#74543D",           # Цвет полей ввода
    'button_bg': "#F45E00",          # Цвет кнопок
    'button_hover': "#D35400",       # Цвет кнопок при наведении
    'text_color': "#FFFFFF",         # Цвет текста
    'placeholder_color': "#D3D3D3",  # Цвет текста-заполнителя
    'link_hover': "green",           # Цвет ссылки при наведении
}

# Минимальная длина для никнейма и пароля
MIN_NICKNAME_LENGTH = 3  # Минимальная длина никнейма
MIN_PASSWORD_LENGTH = 6   # Минимальная длина пароля

# Константы
BUFFER_SIZE = 4096  # Размер буфера для приема данных
CHUNK_SIZE = 1024 * 1024  # Размер чанка (1 МБ)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Добро пожаловать")  # Заголовок окна
        self.geometry("900x600")  # Размер окна

        # Устанавливаем фон приложения
        self.configure(fg_color=COLORS['app_bg'])

        self.socket = None  # Сокет для соединения с сервером
        self.receive_thread = None  # Поток для получения сообщений

        # Создаем контейнер для всех фреймов
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)

        # Настройка сетки
        self.container.grid_rowconfigure(0, weight=1)  # Настройка веса строки
        self.container.grid_columnconfigure(0, weight=1)  # Настройка веса колонки

        # Инициализируем фреймы с передачей необходимых callback-функций
        self.frames = {}
        for F in (LoginFrame, RegisterFrame, ChatFrame):
            if F == LoginFrame:
                frame = F(parent=self.container, controller=self, login_success_callback=self.login_success)
            elif F == RegisterFrame:
                frame = F(parent=self.container, controller=self, register_success_callback=self.register_success)
            else:
                frame = F(parent=self.container, controller=self)
            self.frames[F.__name__] = frame  # Сохраняем фрейм в словаре
            frame.grid(row=0, column=0, sticky="nsew")  # Размещаем фрейм

        # Показываем фрейм входа
        self.show_frame("LoginFrame")  # Отображаем фрейм входа

    def show_frame(self, frame_name, **kwargs):
        """Показывает указанный фрейм."""
        frame = self.frames.get(frame_name)  # Получаем фрейм по имени
        if frame:
            frame.tkraise()  # Поднимаем фрейм на передний план
            if frame_name == "ChatFrame" and 'nickname' in kwargs:
                frame.set_nickname(kwargs['nickname'])  # Устанавливаем никнейм в чате

    def login_success(self, nickname):
        """Обработчик успешного входа."""
        self.show_frame("ChatFrame", nickname=nickname)  # Переход к экрану чата

    def register_success(self, nickname):
        """Обработчик успешной регистрации."""
        messagebox.showinfo("Регистрация", "Аккаунт успешно создан! Пожалуйста, войдите в систему.")  # Сообщение об успешной регистрации
        self.show_frame("LoginFrame")  # Переход к экрану входа

    def connect_to_server(self):
        """Устанавливает TCP-соединение с сервером."""
        server_ip, tcp_port = self.discover_server()  # Обнаруживаем сервер
        if server_ip and tcp_port:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Создаем TCP сокет
                self.socket.connect((server_ip, tcp_port))  # Подключаемся к серверу
                return True  # Успешное подключение
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")  # Сообщение об ошибке
                return False
        else:
            messagebox.showerror("Ошибка", "Не удалось обнаружить сервер.")  # Сообщение об ошибке
            return False

    def discover_server(self):
        """Реализует UDP-обнаружение сервера."""
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Создаем UDP сокет
        udp_socket.settimeout(5)  # Устанавливаем таймаут
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Разрешаем широковещательную рассылку

        message = 'DISCOVER_SERVER'.encode()  # Сообщение для обнаружения сервера
        udp_socket.sendto(message, ('<broadcast>', 37020))  # Отправляем сообщение
        print("Отправлен запрос на обнаружение сервера...")  # Логируем отправку запроса

        try:
            while True:
                data, addr = udp_socket.recvfrom(1024)  # Получаем ответ от сервера
                response = data.decode().strip()  # Декодируем ответ
                print(f"Получен ответ от {addr}: {response}")  # Логируем ответ
                if response.startswith('SERVER_IP'):  # Проверяем, является ли ответ корректным
                    server_info = dict(item.split(':') for item in response.split(';'))  # Парсим информацию о сервере
                    server_ip = server_info['SERVER_IP']  # Получаем IP сервера
                    tcp_port = int(server_info['TCP_PORT'])  # Получаем TCP порт
                    print(f"Найден сервер по адресу {server_ip}:{tcp_port}")  # Логируем найденный сервер
                    return server_ip, tcp_port  # Возвращаем информацию о сервере
        except socket.timeout:
            print("Не удалось обнаружить сервер.")  # Логируем таймаут
            return None, None
        finally:
            udp_socket.close()  # Закрываем сокет

class LoginFrame(ctk.CTkFrame):
    """Экран входа."""

    def __init__(self, parent, controller, login_success_callback):
        super().__init__(parent, corner_radius=15)  # Инициализация фрейма
        self.controller = controller  # Сохраняем контроллер
        self.login_success_callback = login_success_callback  # Сохраняем callback для успешного входа

        # Устанавливаем цвет карточки (формы)
        self.configure(fg_color=COLORS['app_bg'])

        self.create_widgets()  # Создаем элементы интерфейса

    def create_widgets(self):
        """Создает элементы интерфейса для входа."""
        # Центрируем форму
        form_frame = ctk.CTkFrame(self, fg_color=COLORS['card_bg'], corner_radius=15)  # Создаем фрейм для формы
        form_frame.pack(pady=50, padx=100, fill='both', expand=True)  # Размещаем фрейм
        form_frame.pack_propagate(False)  # Фиксируем размеры формы

        # Ограничиваем размеры формы
        form_frame.configure(width=300, height=400)  # Устанавливаем размеры формы

        # Метка заголовка
        self.label = ctk.CTkLabel(
            form_frame,
            text="Вход",  # Заголовок формы
            font=ctk.CTkFont(size=24, weight="bold"),  # Шрифт заголовка
            text_color=COLORS['text_color']  # Цвет текста
        )
        self.label.pack(pady=(20, 10))  # Размещаем заголовок

        # Поля ввода
        self.entries = {}  # Словарь для хранения полей ввода
        fields = [
            {'name': 'nickname', 'placeholder': 'Никнейм'},  # Поле для никнейма
            {'name': 'password', 'placeholder': 'Пароль', 'show': '•'}  # Поле для пароля
        ]
        for field in fields:
            entry = ctk.CTkEntry(
                form_frame,
                placeholder_text=field['placeholder'],  # Текст-заполнитель
                show=field.get('show', None),  # Символ для скрытия пароля
                fg_color=COLORS['entry_bg'],  # Цвет поля ввода
                text_color=COLORS['text_color'],  # Цвет текста
                placeholder_text_color=COLORS['placeholder_color'],  # Цвет текста-заполнителя
                border_width=0,  # Ширина границы
                corner_radius=10  # Радиус углов
            )
            entry.pack(pady=12, padx=50, fill="x")  # Размещаем поле ввода
            self.entries[field['name']] = entry  # Сохраняем поле ввода в словаре

        # Кнопка входа
        self.login_button = ctk.CTkButton(
            form_frame,
            text="Войти",  # Текст кнопки
            command=self.main_action,  # Действие при нажатии
            fg_color=COLORS['button_bg'],  # Цвет кнопки
            hover_color=COLORS['button_hover'],  # Цвет кнопки при наведении
            text_color=COLORS['text_color'],  # Цвет текста
            corner_radius=10  # Радиус углов
        )
        self.login_button.pack(pady=20, padx=50, fill="x")  # Размещаем кнопку

        # Ссылка на регистрацию
        self.bottom_text = ctk.CTkLabel(
            form_frame,
            text="Нет аккаунта?",  # Текст ссылки
            font=ctk.CTkFont(underline=True),  # Подчеркивание текста
            text_color=COLORS['text_color']  # Цвет текста
        )
        self.bottom_text.pack(pady=(30, 5))  # Размещаем ссылку
        self.bottom_text.bind("<Enter>", self.on_enter)  # Обработчик наведения
        self.bottom_text.bind("<Leave>", self.on_leave)  # Обработчик ухода
        self.bottom_text.bind("<Button-1>", lambda e: self.controller.show_frame("RegisterFrame"))  # Переход к регистрации

    def on_enter(self, event):
        self.bottom_text.configure(text_color=COLORS['link_hover'])  # Изменяем цвет текста при наведении

    def on_leave(self, event):
        self.bottom_text.configure(text_color=COLORS['text_color'])  # Возвращаем цвет текста при уходе

    def main_action(self):
        """Обрабатывает нажатие на кнопку 'Войти'."""
        nickname = self.entries['nickname'].get().strip()  # Получаем никнейм
        password = self.entries['password'].get().strip()  # Получаем пароль

        if not nickname or not password:  # Проверка на заполненность полей
            messagebox.showerror("Ошибка", "Пожалуйста, заполните все поля.")  # Сообщение об ошибке
            return
        if len(nickname) < MIN_NICKNAME_LENGTH:  # Проверка длины никнейма
            messagebox.showerror("Ошибка", f"Никнейм должен быть не короче {MIN_NICKNAME_LENGTH} символов.")  # Сообщение об ошибке
            return
        if len(password) < MIN_PASSWORD_LENGTH:  # Проверка длины пароля
            messagebox.showerror("Ошибка", f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов.")  # Сообщение об ошибке
            return

        # Выполняем вход в отдельном потоке
        threading.Thread(target=self.perform_login, args=(nickname, password), daemon=True).start()  # Запускаем поток для входа

    def perform_login(self, nickname, password):
        """Отправляет запрос на вход на сервер."""
        if not self.controller.connect_to_server():  # Подключаемся к серверу
            return
        try:
            login_msg = {'type': 'login', 'nickname': nickname, 'password': password}  # Формируем сообщение для входа
            self.controller.socket.send((json.dumps(login_msg) + '\n').encode())  # Отправляем сообщение
            response_data = self.receive_response()  # Получаем ответ
            if not response_data:  # Проверка на наличие ответа
                messagebox.showerror("Ошибка", "Нет ответа от сервера.")  # Сообщение об ошибке
                return
            response = json.loads(response_data)  # Декодируем ответ
            if response['status'] == 'success':  # Проверка статуса ответа
                self.login_success_callback(nickname)  # Успешный вход
            else:
                messagebox.showerror("Ошибка", response['message'])  # Сообщение об ошибке
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось выполнить вход: {e}")  # Сообщение об ошибке

    def receive_response(self):
        """Принимает одно полное сообщение, разделенное '\n'."""
        buffer = ""  # Буфер для хранения данных
        try:
            while True:
                data = self.controller.socket.recv(BUFFER_SIZE).decode()  # Получаем данные
                if not data:  # Проверка на наличие данных
                    return None
                buffer += data  # Добавляем данные в буфер
                if '\n' in buffer:  # Проверка на наличие разделителя
                    message, buffer = buffer.split('\n', 1)  # Разделяем сообщение
                    return message.strip()  # Возвращаем сообщение
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при получении ответа: {e}")  # Сообщение об ошибке
            return None

class RegisterFrame(ctk.CTkFrame):
    """Экран регистрации."""

    def __init__(self, parent, controller, register_success_callback):
        super().__init__(parent, corner_radius=15)  # Инициализация фрейма
        self.controller = controller  # Сохраняем контроллер
        self.register_success_callback = register_success_callback  # Сохраняем callback для успешной регистрации

        # Устанавливаем цвет карточки (формы)
        self.configure(fg_color=COLORS['app_bg'])

        self.create_widgets()  # Создаем элементы интерфейса

    def create_widgets(self):
        """Создает элементы интерфейса для регистрации."""
        # Центрируем форму
        form_frame = ctk.CTkFrame(self, fg_color=COLORS['card_bg'], corner_radius=15)  # Создаем фрейм для формы
        form_frame.pack(pady=50, padx=100, fill='both', expand=True)  # Размещаем фрейм
        form_frame.pack_propagate(False)  # Фиксируем размеры формы

        # Ограничиваем размеры формы
        form_frame.configure(width=300, height=400)  # Устанавливаем размеры формы

        # Метка заголовка
        self.label = ctk.CTkLabel(
            form_frame,
            text="Регистрация",  # Заголовок формы
            font=ctk.CTkFont(size=24, weight="bold"),  # Шрифт заголовка
            text_color=COLORS['text_color']  # Цвет текста
        )
        self.label.pack(pady=(20, 10))  # Размещаем заголовок

        # Поля ввода
        self.entries = {}  # Словарь для хранения полей ввода
        fields = [
            {'name': 'nickname', 'placeholder': 'Никнейм'},  # Поле для никнейма
            {'name': 'password', 'placeholder': 'Пароль', 'show': '•'},  # Поле для пароля
            {'name': 'confirm_password', 'placeholder': 'Повторите пароль', 'show': '•'}  # Поле для подтверждения пароля
        ]
        for field in fields:
            entry = ctk.CTkEntry(
                form_frame,
                placeholder_text=field['placeholder'],  # Текст-заполнитель
                show=field.get('show', None),  # Символ для скрытия пароля
                fg_color=COLORS['entry_bg'],  # Цвет поля ввода
                text_color=COLORS['text_color'],  # Цвет текста
                placeholder_text_color=COLORS['placeholder_color'],  # Цвет текста-заполнителя
                border_width=0,  # Ширина границы
                corner_radius=10  # Радиус углов
            )
            entry.pack(pady=12, padx=50, fill="x")  # Размещаем поле ввода
            self.entries[field['name']] = entry  # Сохраняем поле ввода в словаре

        # Кнопка регистрации
        self.register_button = ctk.CTkButton(
            form_frame,
            text="Создать аккаунт",  # Текст кнопки
            command=self.main_action,  # Действие при нажатии
            fg_color=COLORS['button_bg'],  # Цвет кнопки
            hover_color=COLORS['button_hover'],  # Цвет кнопки при наведении
            text_color=COLORS['text_color'],  # Цвет текста
            corner_radius=10  # Радиус углов
        )
        self.register_button.pack(pady=20, padx=50, fill="x")  # Размещаем кнопку

        # Ссылка на вход
        self.bottom_text = ctk.CTkLabel(
            form_frame,
            text="Уже есть аккаунт?",  # Текст ссылки
            font=ctk.CTkFont(underline=True),  # Подчеркивание текста
            text_color=COLORS['text_color']  # Цвет текста
        )
        self.bottom_text.pack(pady=(30, 5))  # Размещаем ссылку
        self.bottom_text.bind("<Enter>", self.on_enter)  # Обработчик наведения
        self.bottom_text.bind("<Leave>", self.on_leave)  # Обработчик ухода
        self.bottom_text.bind("<Button-1>", lambda e: self.controller.show_frame("LoginFrame"))  # Переход к входу

    def on_enter(self, event):
        self.bottom_text.configure(text_color=COLORS['link_hover'])  # Изменяем цвет текста при наведении

    def on_leave(self, event):
        self.bottom_text.configure(text_color=COLORS['text_color'])  # Возвращаем цвет текста при уходе

    def main_action(self):
        """Обрабатывает нажатие на кнопку 'Создать аккаунт'."""
        nickname = self.entries['nickname'].get().strip()  # Получаем никнейм
        password = self.entries['password'].get().strip()  # Получаем пароль
        confirm_password = self.entries['confirm_password'].get().strip()  # Получаем подтверждение пароля

        if not nickname or not password or not confirm_password:  # Проверка на заполненность полей
            messagebox.showerror("Ошибка", "Пожалуйста, заполните все поля.")  # Сообщение об ошибке
            return
        if len(nickname) < MIN_NICKNAME_LENGTH:  # Проверка длины никнейма
            messagebox.showerror("Ошибка", f"Никнейм должен быть не короче {MIN_NICKNAME_LENGTH} символов.")  # Сообщение об ошибке
            return
        if len(password) < MIN_PASSWORD_LENGTH:  # Проверка длины пароля
            messagebox.showerror("Ошибка", f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов.")  # Сообщение об ошибке
            return
        if password != confirm_password:  # Проверка на совпадение паролей
            messagebox.showerror("Ошибка", "Пароли не совпадают!")  # Сообщение об ошибке
            return

        # Выполняем регистрацию в отдельном потоке
        threading.Thread(target=self.perform_register, args=(nickname, password), daemon=True).start()  # Запускаем поток для регистрации

    def perform_register(self, nickname, password):
        """Отправляет запрос на регистрацию на сервер."""
        if not self.controller.connect_to_server():  # Подключаемся к серверу
            return
        try:
            register_msg = {'type': 'register', 'nickname': nickname, 'password': password}  # Формируем сообщение для регистрации
            self.controller.socket.send((json.dumps(register_msg) + '\n').encode())  # Отправляем сообщение
            response_data = self.receive_response()  # Получаем ответ
            if not response_data:  # Проверка на наличие ответа
                messagebox.showerror("Ошибка", "Нет ответа от сервера.")  # Сообщение об ошибке
                return
            response = json.loads(response_data)  # Декодируем ответ
            if response['status'] == 'success':  # Проверка статуса ответа
                self.register_success_callback(nickname)  # Успешная регистрация
            else:
                messagebox.showerror("Ошибка", response['message'])  # Сообщение об ошибке
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось зарегистрироваться: {e}")  # Сообщение об ошибке

    def receive_response(self):
        """Принимает одно полное сообщение, разделенное '\n'."""
        buffer = ""  # Буфер для хранения данных
        try:
            while True:
                data = self.controller.socket.recv(BUFFER_SIZE).decode()  # Получаем данные
                if not data:  # Проверка на наличие данных
                    return None
                buffer += data  # Добавляем данные в буфер
                if '\n' in buffer:  # Проверка на наличие разделителя
                    message, buffer = buffer.split('\n', 1)  # Разделяем сообщение
                    return message.strip()  # Возвращаем сообщение
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при получении ответа: {e}")  # Сообщение об ошибке
            return None

class ChatFrame(ctk.CTkFrame):
    """Экран чата."""

    def __init__(self, parent, controller):
        super().__init__(parent)  # Инициализация фрейма
        self.controller = controller  # Сохраняем контроллер
        self.nickname = None  # Никнейм пользователя
        self.server_files = {}  # Словарь для хранения файлов на сервере
        self.current_download = None  # Для отслеживания текущей загрузки
        
        self.configure(fg_color=COLORS['app_bg'])  # Устанавливаем цвет фона
        self.create_widgets()  # Создаем элементы интерфейса

    def set_nickname(self, nickname):
        """Устанавливает никнейм и запускает прием сообщений."""
        self.nickname = nickname  # Сохраняем никнейм
        self.welcome_label.configure(text=f"Йоу, {self.nickname}!")  # Обновляем приветственное сообщение
        # Запускаем поток для получения сообщений
        self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)  # Создаем поток
        self.receive_thread.start()  # Запускаем поток

    def create_widgets(self):
        """Создает элементы интерфейса чата."""
        # Создаем основной контейнер
        main_container = ctk.CTkFrame(self, fg_color=COLORS['app_bg'])  # Создаем фрейм для чата
        main_container.pack(fill="both", expand=True, padx=10, pady=10)  # Размещаем фрейм

        # Настраиваем сетку для разделения экрана
        main_container.grid_columnconfigure(0, weight=7)  # Чат занимает 70% ширины
        main_container.grid_columnconfigure(1, weight=3)  # Файлы занимают 30% ширины
        main_container.grid_rowconfigure(0, weight=1)  # Настройка веса строки

        # Создаем фрейм чата
        self.create_chat_display_frame(main_container)  # Создаем фрейм для отображения чата
        
        # Создаем фрейм для файлов на сервере
        self.create_server_files_frame(main_container)  # Создаем фрейм для отображения файлов

    def create_server_files_frame(self, parent):
        """Создает фрейм для отображения файлов на сервере."""
        # Создаем фрейм для файлов
        files_container = ctk.CTkFrame(parent, fg_color=COLORS['card_bg'], corner_radius=15)  # Фрейм для файлов
        files_container.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)  # Размещаем фрейм
        
        # Настраиваем grid для files_container
        files_container.grid_rowconfigure(1, weight=1)  # Таблица
        files_container.grid_rowconfigure(2, weight=0)  # Системные сообщения
        files_container.grid_columnconfigure(0, weight=1)  # Настройка веса колонки

        # Заголовок
        files_header = ctk.CTkLabel(
            files_container,
            text="Файлы на сервере",  # Заголовок для списка файлов
            font=ctk.CTkFont(size=16, weight="bold"),  # Шрифт заголовка
            text_color=COLORS['text_color']  # Цвет текста
        )
        files_header.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")  # Размещаем заголовок

        # Кнопка обновления списка файлов
        refresh_button = ctk.CTkButton(
            files_container,
            text="Обновить",  # Текст кнопки
            command=self.request_files_list,  # Действие при нажатии
            fg_color=COLORS['button_bg'],  # Цвет кнопки
            hover_color=COLORS['button_hover'],  # Цвет кнопки при наведении
            text_color=COLORS['text_color'],  # Цвет текста
            corner_radius=10,  # Радиус углов
            width=100  # Ширина кнопки
        )
        refresh_button.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="e")  # Размещаем кнопку

        # Создаем Treeview для списка файлов
        self.files_tree = ttk.Treeview(
            files_container,
            columns=("name", "size", "type", "sender", "date"),  # Заголовки колонок
            show="headings",  # Показываем заголовки
            style="Custom.Treeview"  # Стиль таблицы
        )

        # Настраиваем заголовки колонок
        self.files_tree.heading("name", text="Имя файла")  # Заголовок для имени файла
        self.files_tree.heading("size", text="Размер")  # Заголовок для размера
        self.files_tree.heading("type", text="Тип")  # Заголовок для типа
        self.files_tree.heading("sender", text="Отправитель")  # Заголовок для отправителя
        self.files_tree.heading("date", text="Дата")  # Заголовок для даты

        # Настраиваем ширину колонок
        self.files_tree.column("name", width=120)  # Ширина колонки имени файла
        self.files_tree.column("size", width=70)  # Ширина колонки размера
        self.files_tree.column("type", width=70)  # Ширина колонки типа
        self.files_tree.column("sender", width=80)  # Ширина колонки отправителя
        self.files_tree.column("date", width=100)  # Ширина колонки даты

        # Добавляем скроллбар для таблицы
        table_scrollbar = ttk.Scrollbar(files_container, orient="vertical", command=self.files_tree.yview)  # Создаем скроллбар
        self.files_tree.configure(yscrollcommand=table_scrollbar.set)  # Привязываем скроллбар к таблице

        # Размещаем Treeview и скроллбар
        self.files_tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(5, 10))  # Размещаем таблицу
        table_scrollbar.grid(row=1, column=1, sticky="ns", pady=(5, 10), padx=(0, 10))  # Размещаем скроллбар

        # Создаем фрейм для системных сообщений и кнопки
        system_frame = ctk.CTkFrame(files_container, fg_color=COLORS['card_bg'])  # Фрейм для системных сообщений
        system_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))  # Размещаем фрейм

        # Текстовое поле для системных сообщений
        self.system_messages = ctk.CTkTextbox(
            system_frame,
            height=100,  # Высота текстового поля
            fg_color=COLORS['entry_bg'],  # Цвет фона текстового поля
            text_color=COLORS['text_color'],  # Цвет текста
            corner_radius=10,  # Радиус углов
            border_width=0,  # Убираем границы
            state="disabled"  # Делаем поле только для чтения
        )
        self.system_messages.pack(side="left", fill="both", expand=True, padx=(0, 5))  # Размещаем текстовое поле

        # Кнопка скачивания
        download_button = ctk.CTkButton(
            system_frame,
            text="Скачать",  # Текст кнопки
            command=self.download_selected_file,  # Действие при нажатии
            fg_color=COLORS['button_bg'],  # Цвет кнопки
            hover_color=COLORS['button_hover'],  # Цвет кнопки при наведении
            text_color=COLORS['text_color'],  # Цвет текста
            corner_radius=10,  # Радиус углов
            width=100  # Ширина кнопки
        )
        download_button.pack(side="right", padx=(5, 0))  # Размещаем кнопку

    def request_files_list(self):
        """Запрашивает список файлов с сервера."""
        try:
            msg = {'type': 'list_files'}  # Формируем сообщение для запроса списка файлов
            self.controller.socket.send((json.dumps(msg) + '\n').encode())  # Отправляем сообщение
            self.append_system_message("Запрос списка файлов отправлен.")  # Логируем отправку запроса
        except Exception as e:
            self.append_system_message(f"Ошибка при запросе списка файлов: {e}")  # Логируем ошибку
            messagebox.showerror("Ошибка", f"Не удалось запросить список файлов: {e}")  # Сообщение об ошибке

    def display_files_list(self, files):
        """Отображает список файлов в таблице."""
        # Очищаем текущий список
        for item in self.files_tree.get_children():  # Проходим по всем элементам в таблице
            self.files_tree.delete(item)  # Удаляем элемент
        
        # Добавляем новые файлы
        for file_info in files:  # Проходим по всем файлам
            self.add_file_to_table(file_info)  # Добавляем файл в таблицу

    def add_file_to_table(self, file_info):
        """Добавляет файл в таблицу."""
        self.files_tree.insert('', 'end', values=(  # Вставляем новый элемент в таблицу
            file_info['file_name'],  # Имя файла
            file_info['file_size'],  # Размер файла
            file_info['file_type'],  # Тип файла
            file_info['sender'],  # Отправитель
            file_info['date']  # Дата
        ))
        # Сохраняем информацию о файле
        self.server_files[file_info['file_name']] = file_info  # Сохраняем файл в словаре

    def download_selected_file(self):
        """Скачивает выбранный файл."""
        selection = self.files_tree.selection()  # Получаем выбранный элемент
        if not selection:  # Проверка на наличие выбора
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите файл для скачивания.")  # Сообщение об ошибке
            return
        
        item = selection[0]  # Получаем первый выбранный элемент
        file_name = self.files_tree.item(item)['values'][0]  # Получаем имя файла
        
        try:
            msg = {'type': 'download_file', 'file_name': file_name}  # Формируем сообщение для скачивания файла
            self.controller.socket.send((json.dumps(msg) + '\n').encode())  # Отправляем сообщение
            self.append_system_message(f"Запрос на скачивание файла {file_name} отправлен.")  # Логируем отправку запроса
        except Exception as e:
            self.append_system_message(f"Ошибка при запросе файла: {e}")  # Логируем ошибку
            messagebox.showerror("Ошибка", f"Не удалось запросить файл: {e}")  # Сообщение об ошибке

    def download_all_files(self):
        """Скачивает все файлы."""
        if not self.files_tree.get_children():  # Проверка на наличие файлов
            messagebox.showinfo("Информация", "Нет доступных файлов для скачивания.")  # Сообщение об информации
            return
        
        try:
            msg = {'type': 'download_all'}  # Формируем сообщение для скачивания всех файлов
            self.controller.socket.send((json.dumps(msg) + '\n').encode())  # Отправляем сообщение
            self.append_system_message("Запрос на скачивание всех файлов отправлен.")  # Логируем отправку запроса
        except Exception as e:
            self.append_system_message(f"Ошибка при запросе файлов: {e}")  # Логируем ошибку
            messagebox.showerror("Ошибка", f"Не удалось запросить файлы: {e}")  # Сообщение об ошибке

    def prepare_file_download(self, file_info):
        """Подготавливает скачивание файла."""
        save_path = filedialog.asksaveasfilename(  # Открываем диалог для выбора пути сохранения
            initialfile=file_info['file_name'],  # Имя файла по умолчанию
            defaultextension=os.path.splitext(file_info['file_name'])[1]  # Расширение файла
        )
        if save_path:  # Проверка на наличие пути сохранения
            self.current_download = {  # Сохраняем информацию о текущем скачивании
                'file_name': file_info['file_name'],  # Имя файла
                'save_path': save_path,  # Путь сохранения
                'total_chunks': file_info['total_chunks'],  # Общее количество чанков
                'received_chunks': 0,  # Полученные чанки
                'file_data': b''  # Данные файла
            }
        else:
            self.current_download = None  # Сбрасываем текущее скачивание
            self.append_system_message("Скачивание файла отменено.")  # Логируем отмену

    def handle_file_chunk(self, msg):
        """Обрабатывает получение чанка файла."""
        if not self.current_download or msg['file_name'] != self.current_download['file_name']:  # Проверка на соответствие файла
            return
        
        try:
            chunk_data = bytes.fromhex(msg['file_data'])  # Декодируем данные чанка
            self.current_download['file_data'] += chunk_data  # Добавляем данные чанка
            self.current_download['received_chunks'] += 1  # Увеличиваем счетчик полученных чанков
            
            # Обновляем прогресс
            progress = (self.current_download['received_chunks'] / self.current_download['total_chunks']) * 100  # Вычисляем прогресс
            self.append_system_message(f"Получено {progress:.1f}% файла {self.current_download['file_name']}")  # Логируем прогресс
        except Exception as e:
            self.append_system_message(f"Ошибка при обработке чанка файла: {e}")  # Логируем ошибку

    def finalize_file_download(self, msg):
        """Завершает скачивание файла."""
        if not self.current_download or msg['file_name'] != self.current_download['file_name']:  # Проверка на соответствие файла
            return
        
        try:
            with open(self.current_download['save_path'], 'wb') as f:  # Открываем файл для записи
                f.write(self.current_download['file_data'])  # Записываем данные файла
            self.append_system_message(f"Файл {self.current_download['file_name']} успешно сохранён")  # Логируем успешное сохранение
        except Exception as e:
            self.append_system_message(f"Ошибка при сохранении файла: {e}")  # Логируем ошибку
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")  # Сообщение об ошибке
        finally:
            self.current_download = None  # Сбрасываем текущее скачивание

    def receive_messages(self):
        """Получает сообщения от сервера."""
        buffer = ""  # Буфер для хранения данных
        try:
            while True:
                data = self.controller.socket.recv(BUFFER_SIZE).decode()  # Получаем данные
                if not data:  # Проверка на наличие данных
                    break
                buffer += data  # Добавляем данные в буфер
                while '\n' in buffer:  # Проверка на наличие разделителя
                    message, buffer = buffer.split('\n', 1)  # Разделяем сообщение
                    if not message.strip():  # Проверка на пустое сообщение
                        continue
                    msg = json.loads(message)  # Декодируем сообщение
                    
                    if msg['type'] == 'message':  # Обработка сообщения
                        sender = msg.get('sender', 'Unknown')  # Получаем отправителя
                        content = msg.get('content', '')  # Получаем содержимое
                        self.append_message(f"{sender}: {content}")  # Добавляем сообщение в чат
                    
                    elif msg['type'] == 'files_list':  # Обработка списка файлов
                        files = msg.get('files', [])  # Получаем список файлов
                        self.display_files_list(files)  # Отображаем список файлов
                    
                    elif msg['type'] == 'new_file':  # Обработка нового файла
                        self.add_file_to_table(msg)  # Добавляем файл в таблицу
                        self.append_message(f"Новый файл на сервере: {msg['file_name']}")  # Логируем новый файл
                    
                    elif msg['type'] == 'file_info':  # Обработка информации о файле
                        self.prepare_file_download(msg)  # Подготавливаем скачивание файла
                    
                    elif msg['type'] == 'file_chunk':  # Обработка чанка файла
                        self.handle_file_chunk(msg)  # Обрабатываем чанк
                    
                    elif msg['type'] == 'file_complete':  # Обработка завершения скачивания файла
                        self.finalize_file_download(msg)  # Завершаем скачивание
                    
                    else:
                        self.append_message(f"Получено неизвестное сообщение типа: {msg['type']}")  # Логируем неизвестное сообщение
        
        except Exception as e:
            self.append_message(f"Ошибка при получении сообщений: {e}")  # Логируем ошибку
        finally:
            if self.controller.socket:  # Проверка на наличие сокета
                self.controller.socket.close()  # Закрываем сокет
            self.append_message("Соединение с сервером закрыто.")  # Логируем закрытие соединения

    def create_chat_display_frame(self, parent):
        """Создает рамку отображения чата."""
        self.chat_display_frame = ctk.CTkFrame(parent, fg_color=COLORS['card_bg'], corner_radius=15)  # Создаем фрейм для чата
        self.chat_display_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)  # Размещаем фрейм
        self.chat_display_frame.grid_rowconfigure(1, weight=1)  # Настройка веса строки
        self.chat_display_frame.grid_columnconfigure(0, weight=1)  # Настройка веса колонки

        # Приветственный лейбл
        self.welcome_label = ctk.CTkLabel(
            self.chat_display_frame,
            text="Добро пожаловать!",  # Приветственное сообщение
            font=ctk.CTkFont(size=16, weight="bold"),  # Шрифт приветственного сообщения
            text_color=COLORS['text_color']  # Цвет текста
        )
        self.welcome_label.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")  # Размещаем приветственное сообщение

        # Область чата с CTkTextbox
        self.chat_area = ctk.CTkTextbox(
            self.chat_display_frame,
            wrap='word',  # Перенос слов
            fg_color=COLORS['entry_bg'],  # Цвет фона
            text_color=COLORS['text_color'],  # Цвет текста
            font=ctk.CTkFont(size=12),  # Шрифт текста
            border_width=0,  # Убираем границы
            corner_radius=10  # Радиус углов
        )
        self.chat_area.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")  # Размещаем область чата
        self.chat_area.configure(state='disabled')  # Делаем область чата только для чтения
        self.chat_area.bind("<Control-c>", self.copy_text)  # Обработчик копирования текста

        # Рамка ввода сообщений
        self.input_frame = ctk.CTkFrame(self.chat_display_frame, fg_color=COLORS['card_bg'], corner_radius=15)  # Фрейм для ввода сообщений
        self.input_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")  # Размещаем фрейм
        self.input_frame.grid_columnconfigure(0, weight=1)  # Настройка веса колонки
        self.input_frame.grid_columnconfigure(1, weight=0)  # Настройка веса колонки

        # Поле ввода сообщения
        self.message_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Введите сообщение...",  # Текст-заполнитель
            corner_radius=10,  # Радиус углов
            fg_color=COLORS['entry_bg'],  # Цвет поля ввода
            text_color=COLORS['text_color'],  # Цвет текста
            placeholder_text_color=COLORS['placeholder_color'],  # Цвет текста-заполнителя
            border_width=0  # Убираем границы
        )
        self.message_entry.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="ew")  # Размещаем поле ввода
        self.message_entry.bind("<Return>", self.send_message)  # Обработчик нажатия Enter

        # Рамка кнопок
        self.buttons_frame = ctk.CTkFrame(self.input_frame, fg_color=COLORS['card_bg'], corner_radius=10)  # Фрейм для кнопок
        self.buttons_frame.grid(row=0, column=1, padx=(5, 10), pady=5)  # Размещаем фрейм

        # Кнопка прикрепить файл
        self.attach_button = ctk.CTkButton(
            self.buttons_frame,
            text="Файлы",  # Текст кнопки
            command=self.attach_file,  # Действие при нажатии
            fg_color=COLORS['button_bg'],  # Цвет кнопки
            hover_color=COLORS['button_hover'],  # Цвет кнопки при наведении
            text_color=COLORS['text_color'],  # Цвет текста
            corner_radius=10,  # Радиус углов
            width=80  # Ширина кнопки
        )
        self.attach_button.pack(side='left', padx=(0, 5))  # Размещаем кнопку

        # Кнопка отправить сообщение
        self.send_button = ctk.CTkButton(
            self.buttons_frame,
            text="Отправить",  # Текст кнопки
            command=self.send_message,  # Действие при нажатии
            fg_color=COLORS['button_bg'],  # Цвет кнопки
            hover_color=COLORS['button_hover'],  # Цвет кнопки при наведении
            text_color=COLORS['text_color'],  # Цвет текста
            corner_radius=10,  # Радиус углов
            width=80  # Ширина кнопки
        )
        self.send_button.pack(side='left', padx=(5, 0))  # Размещаем кнопку

    def copy_text(self, event):
        """Копирует выделенный текст."""
        try:
            selected = self.chat_area.selection_get()  # Получаем выделенный текст
            self.clipboard_clear()  # Очищаем буфер обмена
            self.clipboard_append(selected)  # Добавляем текст в буфер обмена
        except tk.TclError:
            pass  # Нет выделенного текста

    def append_message(self, message):
        """Добавляет сообщение в чат."""
        self.chat_area.configure(state='normal')  # Разрешаем редактирование области чата
        self.chat_area.insert('end', message + '\n')  # Добавляем сообщение
        self.chat_area.configure(state='disabled')  # Запрещаем редактирование области чата
        self.chat_area.see('end')  # Прокручиваем вниз

    def append_system_message(self, message):
        """Добавляет системное сообщение."""
        self.system_messages.configure(state='normal')  # Разрешаем редактирование текстового поля
        self.system_messages.insert('end', message + '\n')  # Добавляем сообщение
        self.system_messages.configure(state='disabled')  # Запрещаем редактирование текстового поля
        self.system_messages.see('end')  # Прокручиваем вниз

    def send_message(self, event=None):
        """Отправляет сообщение на сервер."""
        message = self.message_entry.get().strip()  # Получаем сообщение
        if message and self.controller.socket:  # Проверка на наличие сообщения и сокета
            try:
                msg = {'type': 'message', 'content': message}  # Формируем сообщение
                self.controller.socket.send((json.dumps(msg) + '\n').encode())  # Отправляем сообщение
                self.append_message(f"Вы: {message}")  # Добавляем сообщение в чат
                self.message_entry.delete(0, 'end')  # Очищаем поле ввода
            except Exception as e:
                self.append_message(f"Ошибка при отправке сообщения: {e}")  # Логируем ошибку
                messagebox.showerror("Ошибка", f"Не удалось отправить сообщение: {e}")  # Сообщение об ошибке

    def attach_file(self):
        """Позволяет пользователю выбрать файл и отправить его на сервер."""
        file_path = filedialog.askopenfilename()  # Открываем диалог для выбора файла
        if file_path:  # Проверка на наличие выбранного файла
            try:
                file_size_bytes = os.path.getsize(file_path)  # Получаем размер файла
                total_chunks = (file_size_bytes // CHUNK_SIZE) + (1 if file_size_bytes % CHUNK_SIZE != 0 else 0)  # Вычисляем количество чанков
                file_name = os.path.basename(file_path)  # Получаем имя файла
                file_type = self.get_file_type(file_path)  # Получаем тип файла
                # Получение текущей даты и времени
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Получаем текущую дату и время

                with open(file_path, 'rb') as f:  # Открываем файл для чтения
                    chunk_number = 1  # Номер чанка
                    while True:
                        file_data = f.read(CHUNK_SIZE)  # Читаем чанк
                        if not file_data:  # Проверка на конец файла
                            break
                        file_data_hex = file_data.hex()  # Преобразуем данные в шестнадцатеричный формат
                        msg = {
                            'type': 'file',  # Тип сообщения
                            'file_name': file_name,  # Имя файла
                            'file_size': self.get_readable_file_size(file_size_bytes),  # Читаемый размер файла
                            'file_type': file_type,  # Тип файла
                            'total_chunks': total_chunks,  # Общее количество чанков
                            'current_chunk': chunk_number,  # Номер текущего чанка
                            'file_data': file_data_hex,  # Данные файла
                            'sender': self.nickname,  # Отправитель
                            'date': current_date  # Дата отправки
                        }
                        self.controller.socket.send((json.dumps(msg) + '\n').encode())  # Отправляем сообщение
                        self.append_message(f"Отправлен файл '{file_name}' Чанк {chunk_number}/{total_chunks}")  # Логируем отправку чанка
                        chunk_number += 1  # Увеличиваем номер чанка
                self.append_message(f"Вы отправили файл: {file_name}")  # Логируем отправку файла
            except Exception as e:
                self.append_message(f"Ошибка при отправке файла: {e}")  # Логируем ошибку
                messagebox.showerror("Ошибка", f"Не удалось отправить файл: {e}")  # Сообщение об ошибке

    def get_readable_file_size(self, size_in_bytes):
        """Преобразует размер файла из байт в читаемый формат."""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:  # Перебираем единицы измерения
            if size_in_bytes < 1024:  # Проверка на размер
                return f"{size_in_bytes} {unit}"  # Возвращаем размер
            size_in_bytes /= 1024  # Делим на 1024 для перехода к следующей единице
        return f"{size_in_bytes:.2f} ПБ"  # Возвращаем размер в ПБ

    def get_file_type(self, file_path):
        """Определяет тип файла по расширению."""
        _, ext = os.path.splitext(file_path)  # Получаем расширение файла
        ext = ext.lower()  # Приводим к нижнему регистру
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:  # Проверка на тип изображения
            return 'Изображение'  # Возвращаем тип
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:  # Проверка на тип видео
            return 'Видео'  # Возвращаем тип
        elif ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.txt']:  # Проверка на тип документа
            return 'Документ'  # Возвращаем тип
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:  # Проверка на тип архива
            return 'Архив'  # Возвращаем тип
        elif ext in ['.mp3', '.wav', '.aac', '.flac']:  # Проверка на тип музыки
            return 'Музыка'  # Возвращаем тип
        else:
            return 'Другой'  # Возвращаем тип по умолчанию

if __name__ == "__main__":
    app = App()  # Создаем экземпляр приложения
    app.mainloop()  # Запускаем главный цикл приложения