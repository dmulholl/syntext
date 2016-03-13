#!/usr/bin/env python3
"""
Unit tests for the syntex module.

Note that this test script requires Python >= 3.4 as it relies on the
TestCase.subTest() functionality introduced to the unittest module in
that version.

"""

import unittest
import syntex
import os
import sys


# Path to the tests directory.
testdir = os.path.join(os.path.dirname(__file__), 'unittests')


# Load a file and return its content.
def load(filepath):
    with open(filepath, encoding='utf-8') as file:
        return file.read()


class TestBasicInput(unittest.TestCase):

    def test_empty_input(self):
        self.assertEqual(syntex.render(''), '')

    def test_whitespace_input(self):
        self.assertEqual(syntex.render(' '), '')

    def test_simple_string_input(self):
        self.assertEqual(syntex.render('foo'), '<p>\nfoo\n</p>')


class TestFiles(unittest.TestCase):

    def test_files(self):
        dirs = [dir for dir in os.listdir(testdir) if not dir.startswith('.')]
        for dirname in dirs:
            for filename in os.listdir(os.path.join(testdir, dirname)):
                base, ext = os.path.splitext(filename)
                if ext == '.txt':
                    text = load(os.path.join(testdir, dirname, base + '.txt'))
                    html = load(os.path.join(testdir, dirname, base + '.html'))
                    with self.subTest(dir=dirname, test=base):
                        self.assertEqual(syntex.render(text), html.strip())


if __name__ == '__main__':
    if sys.version_info < (3, 4):
        sys.exit("Error: test script requires Python version >= 3.4.")
    unittest.main()
