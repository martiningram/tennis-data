from os import getenv
from setuptools import setup
from setuptools import find_packages


setup(
    name='tennis-data',
    version=getenv("VERSION", "LOCAL"),
    description='Provides tennis data',
    packages=find_packages()
)
