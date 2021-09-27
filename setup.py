from setuptools import setup

setup(
    name="comfort",
    install_requires=[
        "erpnext-telegram-integration@git+https://github.com/vrslev/erpnext_telegram.git",
        "ikea-api-wrapped@git+https://github.com/vrslev/ikea-api-wrapped.git@v0.3.7",
        "python-telegram-bot==13.7",
        "vk-api==11.9.2",
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
