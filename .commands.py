import json
import os
import subprocess  # nosec

import click


@click.command()
@click.argument("bench", default="new")
def hello(bench):
    path = f"/Users/lev/benches/{bench}"
    common_site_config = os.path.join(path, "sites", "common_site_config.json")
    if not os.path.exists(common_site_config):
        raise click.BadArgumentUsage("Wrong bench name")
    with open(common_site_config) as fp:
        content = json.load(fp)
    port = content["webserver_port"]

    vscode_path = os.path.join(path, "apps", "comfort")
    if not os.path.exists(vscode_path):
        vscode_path = os.path.join(path, "apps", "cih")
    if not os.path.exists(vscode_path):
        vscode_path = path

    command = """
    brew services start mariadb
    open -a "/Applications/Google Chrome.app" 'http://127.0.0.1:%s'
    cd %s
    code %s
    bench start
    """ % (
        port,
        path,
        vscode_path,
    )
    subprocess.call(command, shell=True)  # nosec


if __name__ == "__main__":
    try:
        hello()
    finally:
        command = "brew services list | grep mariadb | awk '{ print $2}'"
        r = subprocess.check_output(command, shell=True)  # nosec
        if "started" in str(r):
            subprocess.call("brew services stop mariadb", shell=True)  # nosec
