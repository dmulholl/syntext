#!/usr/bin/env python3
"""
Syntext is a lightweight, markdownish markup language for generating HTML from
plain text. This package can be used as both a command line tool and an importable library.

On the command line::

    $ syntext < input.txt > output.html

As a library::

    >>> import syntext
    >>> html = syntext.render(text)

See the `package documentation <http://www.dmulholl.com/docs/syntext/master/>`_ or the
project's `Github homepage <https://github.com/dmulholl/syntext>`_ for
further details.

"""

import os
import re
import io
import setuptools


filepath = os.path.join(os.path.dirname(__file__), 'syntext', '__init__.py')
with io.open(filepath, encoding='utf-8') as metafile:
    regex = r'''^__([a-z]+)__ = ["'](.*)["']'''
    meta = dict(re.findall(regex, metafile.read(), flags=re.MULTILINE))


setuptools.setup(
    name = 'syntext',
    version = meta['version'],
    packages = setuptools.find_packages(),
    entry_points = {
        'console_scripts': [
            'syntext = syntext:main',
        ],
    },
    install_requires = [
        'pygments',
    ],
    author = 'Darren Mulholland',
    url = 'http://www.dmulholl.com/docs/syntext/master/',
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
