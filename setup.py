# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open("README.rst") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="uberlogging",
    version="0.4.0",
    description="Highly opinionated logging configurator",
    long_description=readme,
    author="Zaar Hai",
    author_email="haizaar@haizaar.com",
    url="https://github.com/haizaar/uberlogging",
    license=license,
    packages=find_packages(),
    install_requires=(
        "coloredlogs",
        "structlog",
        "humanfriendly",
        "python-json-logger",
    )
)
