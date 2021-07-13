# This is fork of https://github.com/shariquerik/accounting

if __name__ == "__main__":
    from setuptools import find_packages, setup  # pyright: reportMissingTypeStubs=false
    import toml

    with open("pyproject.toml") as f:
        config = toml.load(f)
    meta = config["tool"]["poetry"]

    setup(
        name=meta["name"],
        version=meta["version"],
        description=meta["description"],
        url=meta["repository"],
        author=meta["authors"][0],
        license=meta["license"],
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
    )
