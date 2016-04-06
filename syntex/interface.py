# -------------------------------------------------------------------------
# This module defines the package's API.
# -------------------------------------------------------------------------

import argparse
import sys
import os
import pprint

from . import utils
from . import parsers
from . import nodes
from . import pkgmeta
from . import toc


# -------------------------------------------------------------------------
# Internal interface.
# -------------------------------------------------------------------------


def parse(text, meta):
    root = nodes.Node()
    root.children = parsers.BlockParser().parse(utils.LineStream(text), meta)
    tocbuilder = toc.TOCBuilder(root)
    meta['toc'] = tocbuilder.toc()
    meta['fulltoc'] = tocbuilder.fulltoc()
    return root


# -------------------------------------------------------------------------
# Library interface.
# -------------------------------------------------------------------------


def render(text, **meta):
    return parse(text, meta).render(meta)


# -------------------------------------------------------------------------
# Command line interface.
# -------------------------------------------------------------------------


# Command line helptext.
helptext = """
Usage: %s [FLAGS]

  Renders input text in Syntex format into HTML. Reads from stdin and
  prints to stdout.

  Example:

    $ syntex < input.txt > output.html

Flags:
  -d, --debug       Run in debug mode.
      --help        Print the application's help text and exit.
  -p, --pygmentize  Add syntax highlighting to code samples.
      --version     Print the application's version number and exit.
""" % os.path.basename(sys.argv[0])


# Custom argparse action to override the default help text.
class HelpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print(helptext.strip())
        sys.exit()


# Entry point for the command line utility.
def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-v', '--version',
        action="version",
        version=pkgmeta.__version__,
    )
    parser.add_argument('-h', '--help',
        action = HelpAction,
        nargs=0,
    )
    parser.add_argument('-d', '--debug',
        action="store_true",
        help="run in debug mode",
    )
    parser.add_argument('-p', '--pygmentize',
        action="store_true",
        help="add syntax highlighting to code samples",
    )
    args = parser.parse_args()

    text = sys.stdin.read()
    meta = {'pygmentize': args.pygmentize}
    root = parse(text, meta)
    html = root.render(meta)

    output = []
    if args.debug:
        output.append(utils.title(' AST '))
        output.append(str(root))
        output.append('\n')
        output.append(utils.title(' META '))
        output.append(pprint.pformat(meta))
        output.append('\n\n')
        output.append(utils.title(' HTML '))
        output.append(html)
    else:
        output.append(html)

    sys.stdout.write(''.join(output))
