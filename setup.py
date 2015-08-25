#!/usr/bin/env python3
"""
Syntex
======

Syntex is a lightweight, markdownish markup language for generating HTML from
plain text. It's implemented in Python 3 and can be used as both a command line
script and a Python library.

On the command line::

    $ syntex < input.txt > output.html

As a Python library::

    import syntex
    html, meta = syntex.render(text)

See the `package documentation <http://pythonhosted.org/syntex/>`_ or the
project's `Github homepage <https://github.com/dmulholland/syntex>`_ for
further details.

"""

import os
import re
import io

from setuptools import setup


filepath = os.path.join(os.path.dirname(__file__), 'syntex.py')
with io.open(filepath, encoding='utf-8') as metafile:
    regex = r'''^__([a-z]+)__ = ["'](.*)["']'''
    meta = dict(re.findall(regex, metafile.read(), flags=re.MULTILINE))


setup(
    name = 'syntex',
    version = meta['version'],
    py_modules = ['syntex'],
    entry_points = {
        'console_scripts': [
            'syntex = syntex:main',
        ],
    },
    install_requires = [
        'Pygments',
        'PyYAML',
    ],
    author = 'Darren Mulholland',
    url = 'https://github.com/dmulholland/syntex',
    license = 'Public Domain',
    description = (
        'A lightweight, markdownish markup language.'
    ),
    long_description = __doc__,
    classifiers = [
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'License :: Public Domain',
        'Topic :: Text Processing :: Markup :: HTML',
    ],
)
