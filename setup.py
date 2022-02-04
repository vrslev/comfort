from setuptools import find_packages, setup

__version__ = "0.38.3"

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
        "ikea-api==1.1.6",
        "pydantic==1.9.0",
        "sentry-sdk==1.5.4",
        "uvicorn[standard]==0.17.1",
    ],
    extras_require={
        "dev": [
            "black==22.1.0",
            "click==7.1.2",  # Black depends on Click 8. It will be here until Frappe supports Click 8.
            "pre_commit==2.17.0",
            "pytest==6.2.5",
            "pytest-cov==3.0.0",
            "pytest-randomly==3.11.0",
            "responses==0.17.0",
        ]
    },
)
