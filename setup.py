from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

from comfort import __version__ as version

setup(
    name="comfort",
    version=version,
    description="Lite-weight ERPNext alternative for specific business",
    author="vrslev",
    author_email="levwint@gmail.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
