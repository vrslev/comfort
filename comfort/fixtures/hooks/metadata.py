from configparser import ConfigParser
from pathlib import Path


def load_metadata():
    """Load required metadata from setup.cfg"""
    path = Path(__file__).parent.parent.parent.parent.joinpath("setup.cfg")
    config = ConfigParser()
    config.read(path)

    meta = config["metadata"]
    app_name, app_description = meta["name"], meta["description"]
    app_title = app_name.capitalize()
    app_publisher = f"{meta['author']} <{meta['author_email']}>"

    return app_name, app_title, app_description, app_publisher
