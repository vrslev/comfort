from setuptools import find_packages, setup

__version__ = "0.30.1"

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
        "ikea-api==1.0.2",
        "pydantic==1.8.2",
        "sentry-sdk==1.5.0",
    ],
    extras_require={
        "dev": [
            "black==21.11b1",
            "pre_commit==2.15.0",
            "pytest==6.2.5",
            "pytest-cov==3.0.0",
            "pytest-randomly==3.10.2",
            "responses==0.16.0",
        ]
    },
)
