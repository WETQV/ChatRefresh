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
ctk.set_appearance_mode("System")  # "System" (light/dark), "Dark", "Light"
ctk.set_default_color_theme("green")  # Используем стандартную тему "green"

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
MIN_NICKNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 6

# Константы для размеров файлов и буферов
SMALL_FILE_THRESHOLD = 1024 * 1024  # 1 MB
MEDIUM_FILE_THRESHOLD = 10 * 1024 * 1024  # 10 MB
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100 MB

SMALL_FILE_BUFFER = 512 * 1024  # 512 KB для файлов < 1 MB
MEDIUM_FILE_BUFFER = 1024 * 1024  # 1 MB для файлов от 1 MB до 10 MB
LARGE_FILE_BUFFER = 2 * 1024 * 1024  # 2 MB для файлов от 10 MB до 100 MB
HUGE_FILE_BUFFER = 4 * 1024 * 1024  # 4 MB для файлов > 100 MB

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Добро пожаловать")
        self.geometry("900x600")  # Увеличенная ширина для лучшей раскладки

        # Устанавливаем фон приложения
        self.configure(fg_color=COLORS['app_bg'])

        self.socket = None
        self.receive_thread = None

        # Создаем контейнер для всех фреймов
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)

        # Настройка сетки
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Инициализируем фреймы с передачей необходимых callback-функций
        self.frames = {}
        for F in (LoginFrame, RegisterFrame, ChatFrame):
            if F == LoginFrame:
                frame = F(parent=self.container, controller=self, login_success_callback=self.login_success)
            elif F == RegisterFrame:
                frame = F(parent=self.container, controller=self, register_success_callback=self.register_success)
            else:
                frame = F(parent=self.container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Показываем фрейм входа
        self.show_frame("LoginFrame")

    def show_frame(self, frame_name, **kwargs):
        """Показывает указанный фрейм."""
        frame = self.frames.get(frame_name)
        if frame:
            frame.tkraise()
            if frame_name == "ChatFrame" and 'nickname' in kwargs:
                frame.set_nickname(kwargs['nickname'])

    def login_success(self, nickname):
        """Обработчик успешного входа."""
        self.show_frame("ChatFrame", nickname=nickname)

    def register_success(self, nickname):
        """Обработчик успешной регистрации."""
        messagebox.showinfo("Регистрация", "Аккаунт успешно создан! Пожалуйста, войдите в систему.")
        self.show_frame("LoginFrame")

    def connect_to_server(self):
        """Устанавливает TCP-соединение с сервером."""
        server_ip, tcp_port = self.discover_server()
        if server_ip and tcp_port:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((server_ip, tcp_port))
                return True
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {e}")
                return False
        else:
            messagebox.showerror("Ошибка", "Не удалось обнаружить сервер.")
            return False

    def discover_server(self):
        """Реализует UDP-обнаружение сервера."""
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(5)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        message = 'DISCOVER_SERVER'.encode()
        udp_socket.sendto(message, ('<broadcast>', 37020))
        print("Отправлен запрос на обнаружение сервера...")

        try:
            while True:
                data, addr = udp_socket.recvfrom(1024)
                response = data.decode().strip()
                print(f"Получен ответ от {addr}: {response}")
                if response.startswith('SERVER_IP'):
                    server_info = dict(item.split(':') for item in response.split(';'))
                    server_ip = server_info['SERVER_IP']
                    tcp_port = int(server_info['TCP_PORT'])
                    print(f"Найден сервер по адресу {server_ip}:{tcp_port}")
                    return server_ip, tcp_port
        except socket.timeout:
            print("Не удалось обнаружить сервер.")
            return None, None
        finally:
            udp_socket.close()

class LoginFrame(ctk.CTkFrame):
    """Экран входа."""

    def __init__(self, parent, controller, login_success_callback):
        super().__init__(parent, corner_radius=15)
        self.controller = controller
        self.login_success_callback = login_success_callback

        # Устанавливаем цвет карточки (формы)
        self.configure(fg_color=COLORS['app_bg'])

        self.create_widgets()

    def create_widgets(self):
        """Создает элементы интерфейса для входа."""
        # Центрируем форму
        form_frame = ctk.CTkFrame(self, fg_color=COLORS['card_bg'], corner_radius=15)
        form_frame.pack(pady=50, padx=100, fill='both', expand=True)
        form_frame.pack_propagate(False)  # Фиксируем размеры формы

        # Ограничиваем размеры формы
        form_frame.configure(width=300, height=400)

        # Метка заголовка
        self.label = ctk.CTkLabel(
            form_frame,
            text="Вход",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS['text_color']
        )
        self.label.pack(pady=(20, 10))

        # Поля ввода
        self.entries = {}
        fields = [
            {'name': 'nickname', 'placeholder': 'Никнейм'},
            {'name': 'password', 'placeholder': 'Пароль', 'show': '•'}
        ]
        for field in fields:
            entry = ctk.CTkEntry(
                form_frame,
                placeholder_text=field['placeholder'],
                show=field.get('show', None),
                fg_color=COLORS['entry_bg'],
                text_color=COLORS['text_color'],
                placeholder_text_color=COLORS['placeholder_color'],
                border_width=0,
                corner_radius=10
            )
            entry.pack(pady=12, padx=50, fill="x")
            self.entries[field['name']] = entry

        # Кнопка входа
        self.login_button = ctk.CTkButton(
            form_frame,
            text="Войти",
            command=self.main_action,
            fg_color=COLORS['button_bg'],
            hover_color=COLORS['button_hover'],
            text_color=COLORS['text_color'],
            corner_radius=10
        )
        self.login_button.pack(pady=20, padx=50, fill="x")

        # Ссылка на регистрацию
        self.bottom_text = ctk.CTkLabel(
            form_frame,
            text="Нет аккаунта?",
            font=ctk.CTkFont(underline=True),
            text_color=COLORS['text_color']
        )
        self.bottom_text.pack(pady=(30, 5))
        self.bottom_text.bind("<Enter>", self.on_enter)
        self.bottom_text.bind("<Leave>", self.on_leave)
        self.bottom_text.bind("<Button-1>", lambda e: self.controller.show_frame("RegisterFrame"))

    def on_enter(self, event):
        self.bottom_text.configure(text_color=COLORS['link_hover'])

    def on_leave(self, event):
        self.bottom_text.configure(text_color=COLORS['text_color'])

    def main_action(self):
        """Обрабатывает нажатие на кнопку 'Войти'."""
        nickname = self.entries['nickname'].get().strip()
        password = self.entries['password'].get().strip()

        if not nickname or not password:
            messagebox.showerror("Ошибка", "Пожалуйста, заполните все поля.")
            return
        if len(nickname) < MIN_NICKNAME_LENGTH:
            messagebox.showerror("Ошибка", f"Никнейм должен быть не короче {MIN_NICKNAME_LENGTH} символов.")
            return
        if len(password) < MIN_PASSWORD_LENGTH:
            messagebox.showerror("Ошибка", f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов.")
            return

        # Выполняем вход в отдельном потоке
        threading.Thread(target=self.perform_login, args=(nickname, password), daemon=True).start()

    def perform_login(self, nickname, password):
        """Отправляет запрос на вход на сервер."""
        if not self.controller.connect_to_server():
            return
        try:
            login_msg = {'type': 'login', 'nickname': nickname, 'password': password}
            self.controller.socket.send((json.dumps(login_msg) + '\n').encode())
            response_data = self.receive_response()
            if not response_data:
                messagebox.showerror("Ошибка", "Нет ответа от сервера.")
                return
            response = json.loads(response_data)
            if response['status'] == 'success':
                self.login_success_callback(nickname)
            else:
                messagebox.showerror("Ошибка", response['message'])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось выполнить вход: {e}")

    def receive_response(self):
        """Принимает одно полное сообщение, разделенное '\n'."""
        buffer = ""
        try:
            while True:
                data = self.controller.socket.recv(4096).decode()
                if not data:
                    return None
                buffer += data
                if '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    return message.strip()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при получении ответа: {e}")
            return None

class RegisterFrame(ctk.CTkFrame):
    """Экран регистрации."""

    def __init__(self, parent, controller, register_success_callback):
        super().__init__(parent, corner_radius=15)
        self.controller = controller
        self.register_success_callback = register_success_callback

        # Устанавливаем цвет карточки (формы)
        self.configure(fg_color=COLORS['app_bg'])

        self.create_widgets()

    def create_widgets(self):
        """Создает элементы интерфейса для регистрации."""
        # Центрируем форму
        form_frame = ctk.CTkFrame(self, fg_color=COLORS['card_bg'], corner_radius=15)
        form_frame.pack(pady=50, padx=100, fill='both', expand=True)
        form_frame.pack_propagate(False)  # Фиксируем размеры формы

        # Ограничиваем размеры формы
        form_frame.configure(width=300, height=400)

        # Метка заголовка
        self.label = ctk.CTkLabel(
            form_frame,
            text="Регистрация",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS['text_color']
        )
        self.label.pack(pady=(20, 10))

        # Поля ввода
        self.entries = {}
        fields = [
            {'name': 'nickname', 'placeholder': 'Никнейм'},
            {'name': 'password', 'placeholder': 'Пароль', 'show': '•'},
            {'name': 'confirm_password', 'placeholder': 'Повторите пароль', 'show': '•'}
        ]
        for field in fields:
            entry = ctk.CTkEntry(
                form_frame,
                placeholder_text=field['placeholder'],
                show=field.get('show', None),
                fg_color=COLORS['entry_bg'],
                text_color=COLORS['text_color'],
                placeholder_text_color=COLORS['placeholder_color'],
                border_width=0,
                corner_radius=10
            )
            entry.pack(pady=12, padx=50, fill="x")
            self.entries[field['name']] = entry

        # Кнопка регистрации
        self.register_button = ctk.CTkButton(
            form_frame,
            text="Создать аккаунт",
            command=self.main_action,
            fg_color=COLORS['button_bg'],
            hover_color=COLORS['button_hover'],
            text_color=COLORS['text_color'],
            corner_radius=10
        )
        self.register_button.pack(pady=20, padx=50, fill="x")

        # Ссылка на вход
        self.bottom_text = ctk.CTkLabel(
            form_frame,
            text="Уже есть аккаунт?",
            font=ctk.CTkFont(underline=True),
            text_color=COLORS['text_color']
        )
        self.bottom_text.pack(pady=(30, 5))
        self.bottom_text.bind("<Enter>", self.on_enter)
        self.bottom_text.bind("<Leave>", self.on_leave)
        self.bottom_text.bind("<Button-1>", lambda e: self.controller.show_frame("LoginFrame"))

    def on_enter(self, event):
        self.bottom_text.configure(text_color=COLORS['link_hover'])

    def on_leave(self, event):
        self.bottom_text.configure(text_color=COLORS['text_color'])

    def main_action(self):
        """Обрабатывает нажатие на кнопку 'Создать аккаунт'."""
        nickname = self.entries['nickname'].get().strip()
        password = self.entries['password'].get().strip()
        confirm_password = self.entries['confirm_password'].get().strip()

        if not nickname or not password or not confirm_password:
            messagebox.showerror("Ошибка", "Пожалуйста, заполните все поля.")
            return
        if len(nickname) < MIN_NICKNAME_LENGTH:
            messagebox.showerror("Ошибка", f"Никнейм должен быть не короче {MIN_NICKNAME_LENGTH} символов.")
            return
        if len(password) < MIN_PASSWORD_LENGTH:
            messagebox.showerror("Ошибка", f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов.")
            return
        if password != confirm_password:
            messagebox.showerror("Ошибка", "Пароли не совпадают!")
            return

        # Выполняем регистрацию в отдельном потоке
        threading.Thread(target=self.perform_register, args=(nickname, password), daemon=True).start()

    def perform_register(self, nickname, password):
        """Отправляет запрос на регистрацию на сервер."""
        if not self.controller.connect_to_server():
            return
        try:
            register_msg = {'type': 'register', 'nickname': nickname, 'password': password}
            self.controller.socket.send((json.dumps(register_msg) + '\n').encode())
            response_data = self.receive_response()
            if not response_data:
                messagebox.showerror("Ошибка", "Нет ответа от сервера.")
                return
            response = json.loads(response_data)
            if response['status'] == 'success':
                self.register_success_callback(nickname)
            else:
                messagebox.showerror("Ошибка", response['message'])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось зарегистрироваться: {e}")

    def receive_response(self):
        """Принимает одно полное сообщение, разделенное '\n'."""
        buffer = ""
        try:
            while True:
                data = self.controller.socket.recv(4096).decode()
                if not data:
                    return None
                buffer += data
                if '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    return message.strip()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при получении ответа: {e}")
            return None

class ChatFrame(ctk.CTkFrame):
    """Экран чата."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.nickname = None
        self.server_files = {}  # file_name: file_info
        self.current_download = None  # Для отслеживания текущей загрузки
        
        self.configure(fg_color=COLORS['app_bg'])
        self.create_widgets()

    def set_nickname(self, nickname):
        """Устанавливает никнейм и запускает прием сообщений."""
        self.nickname = nickname
        self.welcome_label.configure(text=f"Йоу, {self.nickname}!")
        # Запускаем поток для получения сообщений
        self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        self.receive_thread.start()

    def create_widgets(self):
        """Создает элементы интерфейса чата."""
        # Создаем основной контейнер
        main_container = ctk.CTkFrame(self, fg_color=COLORS['app_bg'])
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Настраиваем сетку для разделения экрана
        main_container.grid_columnconfigure(0, weight=7)  # Чат занимает 70% ширины
        main_container.grid_columnconfigure(1, weight=3)  # Файлы занимают 30% ширины
        main_container.grid_rowconfigure(0, weight=1)

        # Создаем фрейм чата
        self.create_chat_display_frame(main_container)
        
        # Создаем фрейм для файлов на сервере
        self.create_server_files_frame(main_container)

    def create_server_files_frame(self, parent):
        """Создает фрейм для отображения файлов на сервере."""
        # Создаем фрейм для файлов
        files_container = ctk.CTkFrame(parent, fg_color=COLORS['card_bg'], corner_radius=15)
        files_container.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        
        # Настраиваем grid для files_container
        files_container.grid_rowconfigure(1, weight=1)  # Таблица
        files_container.grid_rowconfigure(2, weight=0)  # Системные сообщения
        files_container.grid_columnconfigure(0, weight=1)

        # Заголовок
        files_header = ctk.CTkLabel(
            files_container,
            text="Файлы на сервере",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['text_color']
        )
        files_header.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")

        # Кнопка обновления списка файлов
        refresh_button = ctk.CTkButton(
            files_container,
            text="Обновить",
            command=self.request_files_list,
            fg_color=COLORS['button_bg'],
            hover_color=COLORS['button_hover'],
            text_color=COLORS['text_color'],
            corner_radius=10,
            width=100
        )
        refresh_button.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="e")

        # Создаем Treeview для списка файлов
        self.files_tree = ttk.Treeview(
            files_container,
            columns=("name", "size", "type", "sender", "date"),
            show="headings",
            style="Custom.Treeview"
        )

        # Настраиваем заголовки колонок
        self.files_tree.heading("name", text="Имя файла")
        self.files_tree.heading("size", text="Размер")
        self.files_tree.heading("type", text="Тип")
        self.files_tree.heading("sender", text="Отправитель")
        self.files_tree.heading("date", text="Дата")

        # Настраиваем ширину колонок
        self.files_tree.column("name", width=120)
        self.files_tree.column("size", width=70)
        self.files_tree.column("type", width=70)
        self.files_tree.column("sender", width=80)
        self.files_tree.column("date", width=100)

        # Добавляем скроллбар для таблицы
        table_scrollbar = ttk.Scrollbar(files_container, orient="vertical", command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=table_scrollbar.set)

        # Размещаем Treeview и скроллбар
        self.files_tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(5, 10))
        table_scrollbar.grid(row=1, column=1, sticky="ns", pady=(5, 10), padx=(0, 10))

        # Создаем фрейм для системных сообщений и кнопки
        system_frame = ctk.CTkFrame(files_container, fg_color=COLORS['card_bg'])
        system_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        # Текстовое поле для системных сообщений
        self.system_messages = ctk.CTkTextbox(
            system_frame,
            height=100,
            fg_color=COLORS['entry_bg'],
            text_color=COLORS['text_color'],
            corner_radius=10,
            border_width=0,  # Убираем границы
            state="disabled"  # Делаем поле только для чтения
        )
        self.system_messages.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Кнопка скачивания
        download_button = ctk.CTkButton(
            system_frame,
            text="Скачать",
            command=self.download_selected_file,
            fg_color=COLORS['button_bg'],
            hover_color=COLORS['button_hover'],
            text_color=COLORS['text_color'],
            corner_radius=10,
            width=100
        )
        download_button.pack(side="right", padx=(5, 0))

    def request_files_list(self):
        """Запрашивает список файлов с сервера."""
        try:
            msg = {'type': 'list_files'}
            self.controller.socket.send((json.dumps(msg) + '\n').encode())
            self.append_system_message("Запрос списка файлов отправлен.")
        except Exception as e:
            self.append_system_message(f"Ошибка при запросе списка файлов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запросить список файлов: {e}")

    def display_files_list(self, files):
        """Отображает список файлов в таблице."""
        # Очищаем текущий список
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        # Добавляем новые файлы
        for file_info in files:
            self.add_file_to_table(file_info)

    def add_file_to_table(self, file_info):
        """Добавляет файл в таблицу."""
        self.files_tree.insert('', 'end', values=(
            file_info['file_name'],
            file_info['file_size'],
            file_info['file_type'],
            file_info['sender'],
            file_info['date']
        ))
        # Сохраняем информацию о файле
        self.server_files[file_info['file_name']] = file_info

    def download_selected_file(self):
        """Скачивает выбранный файл."""
        selection = self.files_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Пожалуйста, выберите файл для скачивания.")
            return
        
        item = selection[0]
        file_name = self.files_tree.item(item)['values'][0]
        
        try:
            msg = {'type': 'download_file', 'file_name': file_name}
            self.controller.socket.send((json.dumps(msg) + '\n').encode())
            self.append_system_message(f"Запрос на скачивание файла {file_name} отправлен.")
        except Exception as e:
            self.append_system_message(f"Ошибка при запросе файла: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запросить файл: {e}")

    def download_all_files(self):
        """Скачивает все файлы."""
        if not self.files_tree.get_children():
            messagebox.showinfo("Информация", "Нет доступных файлов для скачивания.")
            return
        
        try:
            msg = {'type': 'download_all'}
            self.controller.socket.send((json.dumps(msg) + '\n').encode())
            self.append_system_message("Запрос на скачивание всех файлов отправлен.")
        except Exception as e:
            self.append_system_message(f"Ошибка при запросе файлов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запросить файлы: {e}")

    def prepare_file_download(self, file_info):
        """Подготавливает скачивание файла."""
        save_path = filedialog.asksaveasfilename(
            initialfile=file_info['file_name'],
            defaultextension=os.path.splitext(file_info['file_name'])[1]
        )
        if save_path:
            self.current_download = {
                'file_name': file_info['file_name'],
                'save_path': save_path,
                'total_chunks': file_info['total_chunks'],
                'received_chunks': 0,
                'file_data': b''
            }
        else:
            self.current_download = None
            self.append_system_message("Скачивание файла отменено.")

    def handle_file_chunk(self, msg):
        """Обрабатывает получение чанка файла."""
        if not self.current_download or msg['file_name'] != self.current_download['file_name']:
            return
        
        try:
            chunk_data = bytes.fromhex(msg['file_data'])
            self.current_download['file_data'] += chunk_data
            self.current_download['received_chunks'] += 1
            
            # Обновляем прогресс
            progress = (self.current_download['received_chunks'] / self.current_download['total_chunks']) * 100
            self.append_system_message(f"Получено {progress:.1f}% файла {self.current_download['file_name']}")
        except Exception as e:
            self.append_system_message(f"Ошибка при обработке чанка файла: {e}")

    def finalize_file_download(self, msg):
        """Завершает скачивание файла."""
        if not self.current_download or msg['file_name'] != self.current_download['file_name']:
            return
        
        try:
            with open(self.current_download['save_path'], 'wb') as f:
                f.write(self.current_download['file_data'])
            self.append_system_message(f"Файл {self.current_download['file_name']} успешно сохранён")
        except Exception as e:
            self.append_system_message(f"Ошибка при сохранении файла: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
        finally:
            self.current_download = None

    def receive_messages(self):
        """Получает сообщения от сервера."""
        buffer = ""
        try:
            while True:
                data = self.controller.socket.recv(4096).decode()
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    if not message.strip():
                        continue
                    msg = json.loads(message)
                    
                    if msg['type'] == 'message':
                        sender = msg.get('sender', 'Unknown')
                        content = msg.get('content', '')
                        self.append_message(f"{sender}: {content}")
                    
                    elif msg['type'] == 'files_list':
                        files = msg.get('files', [])
                        self.display_files_list(files)
                    
                    elif msg['type'] == 'new_file':
                        self.add_file_to_table(msg)
                        self.append_message(f"Новый файл на сервере: {msg['file_name']}")
                    
                    elif msg['type'] == 'file_info':
                        self.prepare_file_download(msg)
                    
                    elif msg['type'] == 'file_chunk':
                        self.handle_file_chunk(msg)
                    
                    elif msg['type'] == 'file_complete':
                        self.finalize_file_download(msg)
                    
                    else:
                        self.append_message(f"Получено неизвестное сообщение типа: {msg['type']}")
        
        except Exception as e:
            self.append_message(f"Ошибка при получении сообщений: {e}")
        finally:
            if self.controller.socket:
                self.controller.socket.close()
            self.append_message("Соединение с сервером закрыто.")

    def create_chat_display_frame(self, parent):
        """Создает рамку отображения чата."""
        self.chat_display_frame = ctk.CTkFrame(parent, fg_color=COLORS['card_bg'], corner_radius=15)
        self.chat_display_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.chat_display_frame.grid_rowconfigure(1, weight=1)
        self.chat_display_frame.grid_columnconfigure(0, weight=1)

        # Приветственный лейбл
        self.welcome_label = ctk.CTkLabel(
            self.chat_display_frame,
            text="Добро пожаловать!",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['text_color']
        )
        self.welcome_label.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")

        # Область чата с CTkTextbox
        self.chat_area = ctk.CTkTextbox(
            self.chat_display_frame,
            wrap='word',
            fg_color=COLORS['entry_bg'],
            text_color=COLORS['text_color'],
            font=ctk.CTkFont(size=12),
            border_width=0,  # Убираем границы
            corner_radius=10
        )
        self.chat_area.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.chat_area.configure(state='disabled')
        self.chat_area.bind("<Control-c>", self.copy_text)

        # Рамка ввода сообщений
        self.input_frame = ctk.CTkFrame(self.chat_display_frame, fg_color=COLORS['card_bg'], corner_radius=15)
        self.input_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_columnconfigure(1, weight=0)

        # Поле ввода сообщения
        self.message_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Введите сообщение...",
            corner_radius=10,
            fg_color=COLORS['entry_bg'],
            text_color=COLORS['text_color'],
            placeholder_text_color=COLORS['placeholder_color'],
            border_width=0  # Убираем границы
        )
        self.message_entry.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="ew")
        self.message_entry.bind("<Return>", self.send_message)

        # Рамка кнопок
        self.buttons_frame = ctk.CTkFrame(self.input_frame, fg_color=COLORS['card_bg'], corner_radius=10)
        self.buttons_frame.grid(row=0, column=1, padx=(5, 10), pady=5)

        # Кнопка прикрепить файл
        self.attach_button = ctk.CTkButton(
            self.buttons_frame,
            text="Файлы",
            command=self.attach_file,
            fg_color=COLORS['button_bg'],
            hover_color=COLORS['button_hover'],
            text_color=COLORS['text_color'],
            corner_radius=10,
            width=80
        )
        self.attach_button.pack(side='left', padx=(0, 5))

        # Кнопка отправить сообщение
        self.send_button = ctk.CTkButton(
            self.buttons_frame,
            text="Отправить",
            command=self.send_message,
            fg_color=COLORS['button_bg'],
            hover_color=COLORS['button_hover'],
            text_color=COLORS['text_color'],
            corner_radius=10,
            width=80
        )
        self.send_button.pack(side='left', padx=(5, 0))

    def copy_text(self, event):
        """Копирует выделенный текст."""
        try:
            selected = self.chat_area.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected)
        except tk.TclError:
            pass  # Нет выделенного текста

    def append_message(self, message):
        """Добавляет сообщение в чат."""
        self.chat_area.configure(state='normal')
        self.chat_area.insert('end', message + '\n')
        self.chat_area.configure(state='disabled')
        self.chat_area.see('end')

    def append_system_message(self, message):
        """Добавляет системное сообщение."""
        self.system_messages.configure(state='normal')
        self.system_messages.insert('end', message + '\n')
        self.system_messages.configure(state='disabled')
        self.system_messages.see('end')

    def send_message(self, event=None):
        """Отправляет сообщение на сервер."""
        message = self.message_entry.get().strip()
        if message and self.controller.socket:
            try:
                msg = {'type': 'message', 'content': message}
                self.controller.socket.send((json.dumps(msg) + '\n').encode())
                self.append_message(f"Вы: {message}")
                self.message_entry.delete(0, 'end')
            except Exception as e:
                self.append_message(f"Ошибка при отправке сообщения: {e}")
                messagebox.showerror("Ошибка", f"Не удалось отправить сообщение: {e}")

    def attach_file(self):
        """Позволяет пользователю выбрать файл и отправить его на сервер."""
        file_path = filedialog.askopenfilename()
        if file_path:
            # Создаем и запускаем поток для отправки файла
            upload_thread = threading.Thread(
                target=self.upload_file,
                args=(file_path,),
                daemon=True
            )
            upload_thread.start()
            self.append_system_message(f"Начата отправка файла: {os.path.basename(file_path)}")

    def upload_file(self, file_path):
        """Отправляет файл в отдельном потоке."""
        try:
            file_size = os.path.getsize(file_path)
            buffer_size = self.get_buffer_size(file_size)
            total_chunks = (file_size // buffer_size) + (1 if file_size % buffer_size != 0 else 0)
            
            with open(file_path, 'rb') as f:
                chunk_number = 1
                while True:
                    file_data = f.read(buffer_size)
                    if not file_data:
                        break
                    
                    file_data_hex = file_data.hex()
                    msg = {
                        'type': 'file',
                        'file_name': os.path.basename(file_path),
                        'file_size': self.get_readable_file_size(file_size),
                        'total_chunks': total_chunks,
                        'current_chunk': chunk_number,
                        'file_data': file_data_hex,
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.send_message_to_server(msg)
                    # Отправляем информацию о прогрессе в системные сообщения
                    self.append_system_message(
                        f"Прогресс отправки '{os.path.basename(file_path)}': {chunk_number}/{total_chunks}"
                    )
                    chunk_number += 1
            
            self.append_message(f"Вы отправили файл: {os.path.basename(file_path)}")
        except Exception as e:
            self.append_system_message(f"Ошибка при отправке файла: {e}")
            messagebox.showerror("Ошибка", f"Не удалось отправить файл: {e}")

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

    def send_message_to_server(self, msg):
        """Отправляет сообщение на сервер."""
        try:
            self.controller.socket.send((json.dumps(msg) + '\n').encode())
        except Exception as e:
            self.append_message(f"Ошибка при отправке сообщения: {e}")
            messagebox.showerror("Ошибка", f"Не удалось отправить сообщение: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()