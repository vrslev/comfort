from setuptools import find_packages, setup

__version__ = "0.40.3"

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
        "ikea-api[httpx]==2.0.5",
        "pydantic==1.9.0",
        "sentry-sdk==1.5.6",
        "uvicorn[standard]==0.17.5",
    ],
    extras_require={
        "dev": [
            "black==21.12b0",
            "pre_commit==2.17.0",
            "pytest==7.1.0",
            "pytest-cov==3.0.0",
            "pytest-randomly==3.11.0",
            "responses==0.18.0",
        ]
    },
)
