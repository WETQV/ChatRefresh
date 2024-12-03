# server/utils.py

import socket
import logging

try:
    import miniupnpc
except ImportError:
    miniupnpc = None

logger = logging.getLogger(__name__)

def get_server_ip(client_ip):
    """Получает IP-адрес сервера, используемый для связи с клиентом."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((client_ip, 1))
        server_ip = s.getsockname()[0]
    except Exception:
        server_ip = '127.0.0.1'
    finally:
        s.close()
    return server_ip

def setup_upnp(tcp_port):
    """Автоматически открывает порт через UPnP, если поддерживается."""
    if not miniupnpc:
        logger.warning("Модуль miniupnpc не установлен. UPnP не будет настроен.")
        return False

    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        ndevices = upnp.discover()
        logger.info(f"Найдено {ndevices} UPnP устройств.")
        upnp.selectigd()
        external_ip = upnp.externalipaddress()
        logger.info(f"Внешний IP адрес: {external_ip}")
        existing_port = upnp.getspecificportmapping(tcp_port, 'TCP')
        if existing_port:
            logger.info(f"Порт {tcp_port} уже открыт на маршрутизаторе.")
            return True
        upnp.addportmapping(tcp_port, 'TCP', upnp.lanaddr, tcp_port, 'ChatServer', '')
        logger.info(f"Порт {tcp_port} успешно открыт через UPnP.")
        return True
    except Exception as e:
        logger.error(f"Не удалось настроить UPnP: {e}")
        return False