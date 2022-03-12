#!/usr/bin/env python
from setuptools import setup


setup(
    name="namely",
    version="1.0",
    description="Yet another file renamer",
    author="David Krauth",
    author_email="dakrauth@gmail.com",
    url="https://github.com/dakrauth/namely",
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    license='MIT',
    py_modules = ['namely'],
    zip_safe=False,
    entry_points={
        'console_scripts': ['namely=namely:main']
    },
)
