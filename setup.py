#!/usr/bin/env python3
"""
Monk
====

Monk is a lightweight, markdownish markup language for generating HTML from
plain text. It's implemented in Python 3 and can be used as both a command line
tool and a Python library.

On the command line::

    $ monk < input.txt > output.html

As a library::

    >>> import monk
    >>> html = monk.render(text)

See the `package documentation <http://mulholland.xyz/docs/monk/>`_ or the
project's `Github homepage <https://github.com/dmulholland/monk>`_ for
further details.

"""

import os
import re
import io

from setuptools import setup, find_packages


filepath = os.path.join(os.path.dirname(__file__), 'monk', '__init__.py')
with io.open(filepath, encoding='utf-8') as metafile:
    regex = r'''^__([a-z]+)__ = ["'](.*)["']'''
    meta = dict(re.findall(regex, metafile.read(), flags=re.MULTILINE))


setup(
    name = 'libmonk',
    version = meta['version'],
    packages =  find_packages(),
    entry_points = {
        'console_scripts': [
            'monk = monk:main',
        ],
    },
    install_requires = [
        'pygments',
    ],
    author = 'Darren Mulholland',
    url = 'http://mulholland.xyz/docs/monk/',
    license = 'Public Domain',
    description = ('A markdownish markup language.'),
    long_description = __doc__,
    classifiers = [
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: Public Domain',
        'Topic :: Text Processing :: Markup :: HTML',
    ],
)
