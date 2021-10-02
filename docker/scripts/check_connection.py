from __future__ import annotations

import json
import socket
import time
from typing import Any
from urllib.parse import urlparse

RETRY = 30
DELAY = 3


def _port_is_open(ip: str, port: str):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(30)
    try:
        s.connect((ip, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except Exception:
        return False
    finally:
        s.close()


def check_service(host: str, port: str | int):
    port = str(port)
    for i in range(RETRY):
        print(f"Attempt {i + 1} to connect to {host}:{port}")
        if _port_is_open(host, port):
            print(f"Connected to {host}:{port}")
            return
        time.sleep(DELAY)
    print(f"Connection to {host}:{port} timed out")
    raise SystemExit(1)


def _get_config() -> dict[str, Any]:
    with open("common_site_config.json") as config_file:
        return json.load(config_file)


def check_db():
    config = _get_config()
    host: str = config.get("db_host", "mariadb")
    port: int = config.get("db_port", 3306)
    check_service(host, port)


def _check_redis(config_key: str, default_value: str):
    url = urlparse(_get_config().get(config_key, default_value)).netloc
    host, port = url.split(":")
    check_service(host, port)


def check_all_redises():
    for redis in (
        ("redis_queue", "redis://redis-queue:6379"),
        ("redis_cache", "redis://redis-cache:6379"),
        ("redis_socketio", "redis://redis-socketio:6379"),
    ):
        _check_redis(*redis)


def main():
    check_db()
    check_all_redises()
    print("Connections OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
