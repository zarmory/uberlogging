#!/usr/bin/env python

from setuptools import find_packages, setup

with open("README.rst") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="uberlogging",
    version="0.7.0",
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
    ),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
    ],
)
