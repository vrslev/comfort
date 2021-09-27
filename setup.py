from setuptools import setup

setup(
    name="comfort",
    install_requires=[
        "erpnext-telegram-integration@git+https://github.com/vrslev/erpnext_telegram.git",
        "ikea-api-wrapped@git+https://github.com/vrslev/ikea-api-wrapped.git@v0.3.7",
        "python-telegram-bot==13.7",
        "vk-api==11.9.2",
    ],
)
