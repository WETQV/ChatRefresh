# Chat Refresh

Простой чат с графическим интерфейсом, построенный на Python. Поддерживает обмен сообщениями и файлами между пользователями.

## Возможности

- Регистрация и авторизация пользователей
- Обмен текстовыми сообщениями
- Отправка и получение файлов
- Простенький графический интерфейс на CustomTkinter
- Система поиска сервера через UDP
- Работает в локальной сети

![Авторизация](images/photo_Authorization.jpg)

![Регистрация](images/photo_Registration.jpg)

![Чат](images/photo_Chat.jpg)

## Структура проекта

```
Chat_refresh/
├── client/             # Клиентская часть
│   └── client.py       # Основной файл клиента
├── server/             # Серверная часть
│   ├── server.py       # Основной файл сервера
│   ├── handlers.py     # Обработчики подключений
│   ├── database.py     # Работа с базой данных
│   └── utils.py        # Вспомогательные функции
└── requirements.txt    # Зависимости проекта
```

## Установка

1. Клонируйте репозиторий:
```bash
git clone <https://github.com/WETQV/ChatRefresh.git>
cd Chat_refresh
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv .venv
.venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Запуск

1. Запустите сервер:
```bash
python server/server.py
```

2. Запустите клиент:
```bash
python client/client.py
```

## Лицензия

[Apache](LICENSE)
