from __future__ import annotations

import argparse

import check_connection
from check_connection import check_all_redises, check_db, check_service


def _get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--ping-service",
        dest="ping_services",
        action="append",
        type=str,
        help='list of services to ping, e.g. doctor -p "postgres:5432" --ping-service "mariadb:3306"',
    )
    return parser.parse_args()


def main():
    args = _get_args()

    check_connection.RETRY, check_connection.DELAY = 1, 0

    check_db()
    check_all_redises()

    services: list[str] | None = args.ping_services
    if services:
        for service in services:
            try:
                host, port = service.split(":")
            except ValueError:
                print("Service should be in format host:port, e.g. postgres:5432")
                return 1
            check_service(host, port)

    print("Health check successful")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
