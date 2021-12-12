from setuptools import find_packages, setup

__version__ = "0.32.4"

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
        "ikea-api==1.0.3",
        "pydantic==1.8.2",
        "sentry-sdk==1.5.0",
    ],
    extras_require={
        "dev": [
            "black==21.12b0",
            "pre_commit==2.16.0",
            "pytest==6.2.5",
            "pytest-cov==3.0.0",
            "pytest-randomly==3.10.3",
            "responses==0.16.0",
        ]
    },
)
