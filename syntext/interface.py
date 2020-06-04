# ------------------------------------------------------------------------------
# This module defines the package's API.
# ------------------------------------------------------------------------------

import argparse
import sys
import os
import pprint
import syntext

from . import utils
from . import parsers
from . import nodes
from . import toc
from . import escapes


# ------------------------------------------------------------------------------
# Internal interface.
# ------------------------------------------------------------------------------


def parse(text, meta):
    expanded_text = text.expandtabs(meta.get('tabsize', 4))
    escaped_text = escapes.escapechars(expanded_text)
    line_stream = utils.LineStream(escaped_text)
    root = nodes.Node()
    root.children = parsers.BlockParser().parse(line_stream, meta)
    tocbuilder = toc.TOCBuilder(root)
    meta['toc'] = tocbuilder.toc()
    meta['fulltoc'] = tocbuilder.fulltoc()
    html = root.render(meta)
    html = escapes.unescapechars(html)
    return html.strip(), root, meta


# ------------------------------------------------------------------------------
# Library interface.
# ------------------------------------------------------------------------------


def render(text, **meta):
    html, _, _ = parse(text, meta)
    return html


# ------------------------------------------------------------------------------
# Command line interface.
# ------------------------------------------------------------------------------


# Command line helptext.
helptext = """
Usage: %s [FLAGS] [OPTIONS]

  Renders input text in Syntext format into HTML. Reads from stdin and
  prints to stdout.

  Example:

    $ syntext < input.txt > output.html

Options:
  -t, --tabsize <n>     Set tab translation size (default: 4).

Flags:
  -d, --debug           Run in debug mode.
  -h, --help            Print the application's help text and exit.
  -p, --pygmentize      Add syntax highlighting to code samples.
  -v, --version         Print the application's version number and exit.
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
        version=syntext.__version__,
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
    parser.add_argument('-t', '--tabsize',
        type=int,
        default=4,
        help="set tabsize",
    )
    args = parser.parse_args()

    text = sys.stdin.read()
    meta = {
        'pygmentize': args.pygmentize,
        'tabsize': args.tabsize,
    }
    html, root, meta = parse(text, meta)

    if args.debug:
        print(utils.title('AST'))
        print(root)
        print(utils.title('META'))
        print(pprint.pformat(meta) + '\n')
        print(utils.title('HTML'))
        print(html)
    else:
        print(html)

