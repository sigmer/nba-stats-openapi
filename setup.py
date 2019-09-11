import os
from setuptools import setup


def read(file_name):
    """Read a text file and return the content as a string."""
    with open(os.path.join(os.path.dirname(__file__), file_name),
              encoding='utf-8') as f:
        return f.read().strip()


setup(version=read('VERSION'))
