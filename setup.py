from setuptools import find_packages, setup

__version__ = "0.2.0"

setup(
    name="comfort",
    version=__version__,
    description="Lite-weight ERPNext alternative for specific business",
    author="Lev Vereshchagin",
    author_email="mail@vrslev.com",
    packages=find_packages(),
    include_package_data=True,
    package_data={"": ["*.md", "*.json", "*.txt", "*.css", "*.csv", "*.html", "*.js"]},
    zip_safe=False,
    install_requires=[
        "ikea-api-wrapped@git+https://github.com/vrslev/ikea-api-wrapped.git@v0.4.0",
        "python-telegram-bot==13.7",
        "sentry-sdk==1.4.3",
    ],
    extras_require={
        "dev": [
            "black==21.9b0",
            "pre_commit==2.15.0",
            "pytest==6.2.5",
            "pytest-cov==3.0.0",
            "pytest-randomly==3.10.1",
            "responses==0.14.0",
        ]
    },
)
