from setuptools import setup

__version__ = "0.0.1"

setup(
    name="comfort_browser_ext",
    version=__version__,
    author="Lev Vereshchagin",
    author_email="mail@vrslev.com",
    zip_safe=False,
    py_modules=["comfort_browser_ext"],
    install_requires=[
        "ikea-api-wrapped@git+https://github.com/vrslev/ikea-api-wrapped.git@v0.3.10",
        "frappeclient@git+https://github.com/frappe/frappe-client.git@88ed95c472a1ce8ca05c38b29e97cf8c3ece7054#egg=frappeclient",
        "beautifulsoup4==4.10.0",
        "sentry-sdk==1.4.3",
    ],
    extras_require={
        "dev": [
            "black==21.9b0",
            "pre_commit==2.15.0",
            "pytest==6.2.5",
            "pytest-cov==2.12.1",
            "pytest-randomly==3.10.1",
        ]
    },
)