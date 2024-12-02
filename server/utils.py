# server/utils.py

import socket
import logging

try:
    import miniupnpc  # Импортируем библиотеку для работы с UPnP
except ImportError:
    miniupnpc = None  # Если библиотека не установлена, устанавливаем значение None

logger = logging.getLogger(__name__)  # Создаем логгер для текущего модуля

def get_server_ip(client_ip):
    """Получает IP-адрес сервера, используемый для связи с клиентом."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Создаем UDP сокет
    try:
        s.connect((client_ip, 1))  # Подключаемся к указанному IP-адресу клиента
        server_ip = s.getsockname()[0]  # Получаем локальный IP-адрес сервера
    except Exception:
        server_ip = '127.0.0.1'  # Если произошла ошибка, используем локальный адрес
    finally:
        s.close()  # Закрываем сокет
    return server_ip  # Возвращаем IP-адрес сервера

def setup_upnp(tcp_port):
    """Автоматически открывает порт через UPnP, если поддерживается."""
    if not miniupnpc:  # Проверяем, установлен ли модуль miniupnpc
        logger.warning("Модуль miniupnpc не установлен. UPnP не будет настроен.")  # Логируем предупреждение
        return False  # Возвращаем False, если модуль не установлен

    try:
        upnp = miniupnpc.UPnP()  # Создаем объект UPnP
        upnp.discoverdelay = 200  # Устанавливаем задержку для обнаружения устройств
        ndevices = upnp.discover()  # Обнаруживаем UPnP устройства
        logger.info(f"Найдено {ndevices} UPnP устройств.")  # Логируем количество найденных устройств
        upnp.selectigd()  # Выбираем маршрутизатор для настройки
        external_ip = upnp.externalipaddress()  # Получаем внешний IP-адрес
        logger.info(f"Внешний IP адрес: {external_ip}")  # Логируем внешний IP-адрес
        existing_port = upnp.getspecificportmapping(tcp_port, 'TCP')  # Проверяем, открыт ли порт
        if existing_port:  # Если порт уже открыт
            logger.info(f"Порт {tcp_port} уже открыт на маршрутизаторе.")  # Логируем информацию о порте
            return True  # Возвращаем True
        upnp.addportmapping(tcp_port, 'TCP', upnp.lanaddr, tcp_port, 'ChatServer', '')  # Открываем порт
        logger.info(f"Порт {tcp_port} успешно открыт через UPnP.")  # Логируем успешное открытие порта
        return True  # Возвращаем True
    except Exception as e:
        logger.error(f"Не удалось настроить UPnP: {e}")  # Логируем ошибку
        return False  # Возвращаем False в случае ошибки