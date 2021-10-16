from setuptools import setup

__version__ = "0.1.1"

setup(
    name="comfort_browser_ext",
    version=__version__,
    author="Lev Vereshchagin",
    author_email="mail@vrslev.com",
    zip_safe=False,
    py_modules=["comfort_browser_ext"],
    install_requires=[
        "ikea-api-wrapped@git+https://github.com/vrslev/ikea-api-wrapped.git@v0.4.0",
        "beautifulsoup4==4.10.0",
        "sentry-sdk==1.4.3",
    ],
    extras_require={
        "dev": [
            "pytest==6.2.5",
            "pytest-cov==3.0.0",
            "pytest-randomly==3.10.1",
            "responses==0.14.0",
        ]
    },
)
