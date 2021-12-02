import json
import os.path
import subprocess  # nosec
from typing import Any

path = "/Users/lev/bench"


def call(args: str):
    code = subprocess.call(args, shell=True)  # nosec
    if code != 0:
        raise Exception(f'"{args}" returned with code {code}')


def is_db_running():
    output = subprocess.check_output(  # nosec
        "brew services list | grep mariadb | awk '{ print $2}'", shell=True
    )
    return "started" in str(output)


def start_db():
    if not is_db_running():
        call("brew services start mariadb")


def stop_db():
    if is_db_running():
        call("brew services stop mariadb")


def get_port() -> int:
    with open(os.path.join(path, "sites", "common_site_config.json")) as f:
        config: dict[str, Any] = json.load(f)
    return config["webserver_port"]


def open_browser():
    call(f'open -a "/Applications/Google Chrome.app" http://127.0.0.1:{get_port()}/app')


def open_vscode():
    call(f"code {path}/apps/comfort")


def start_bench():
    call(f"cd {path}; bench start")


def main():
    try:
        start_db()
        open_browser()
        open_vscode()
        start_bench()
    finally:
        stop_db()
        raise SystemExit(0)


if __name__ == "__main__":
    main()
