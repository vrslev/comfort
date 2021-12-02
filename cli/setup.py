from setuptools import setup

__version__ = "0.1.0"

setup(
    name="comfort_cli",
    version=__version__,
    author="Lev Vereshchagin",
    author_email="mail@vrslev.com",
    zip_safe=False,
    py_modules=["comfort_cli"],
    entry_points={"console_scripts": ["comfort=comfort_cli:main"]},
)
