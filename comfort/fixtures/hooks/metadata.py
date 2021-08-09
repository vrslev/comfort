import pathlib

import toml


def load_metadata():
    with open(
        pathlib.Path(__file__).parent.parent.parent.parent.joinpath("pyproject.toml")
    ) as f:
        content = toml.load(f)
    poetry_metadata = content["tool"]["poetry"]
    app_name: str = poetry_metadata["name"]
    app_title = app_name.capitalize()
    app_publisher = poetry_metadata["authors"][0]
    app_description = poetry_metadata["description"]
    return app_name, app_title, app_description, app_publisher
