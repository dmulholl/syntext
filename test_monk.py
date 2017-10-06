#!/usr/bin/env python3
# -------------------------------------------------------------------------
# Unit tests for the monk package.
# -------------------------------------------------------------------------

import monk
import os
import sys


# Path to the tests directory.
testdir = os.path.join(os.path.dirname(__file__), 'unittests')


# Load a file and return its content as a string.
def load(filepath):
    with open(filepath, encoding='utf-8') as file:
        return file.read()


# Load and render the suite of test-input files.
def main():
    oks, fails = 0, 0

    print('''
--------------------------------------------------------------------------------
    Directory    |                     File                      |    Result
--------------------------------------------------------------------------------
'''.strip())

    directories = [dn for dn in os.listdir(testdir) if not dn.startswith('.')]
    for directory in directories:
        files = os.listdir(os.path.join(testdir, directory, 'text'))
        files = [fn for fn in files if not fn.startswith('.')]
        for filename in files:
            textfile = os.path.join(testdir, directory, 'text', filename)
            htmlfile = os.path.join(testdir, directory, 'html', filename)
            if os.path.isfile(htmlfile):
                text = load(textfile)
                html = load(htmlfile)
                if monk.render(text).strip() == html.strip():
                    oks += 1
                    result = 'ok'
                else:
                    fails += 1
                    result = 'fail'
            else:
                fails += 1
                result = '??????'
            output  = '    '
            output += directory.ljust(18)
            output += filename.ljust(48)
            output += result.center(6)
            print(output)

    result = 'FAIL' if fails else 'OK'
    print('-' * 80)
    output  = ('    %s/%s' % (oks, oks + fails)).ljust(70)
    output += result.center(6)
    print(output)
    print('-' * 80)
    if fails:
        sys.exit(1)


if __name__ == '__main__':
    main()
