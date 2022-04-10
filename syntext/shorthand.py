# ------------------------------------------------------------------------------
# Functions for processing shorthand html tags.
# ------------------------------------------------------------------------------

import html
import re

from . import nodes
from . import parsers
from . import utils


# Void elements have no content or closing tag.
html_void_tags = set("""
    area base br col embed hr img input link meta param source track wbr
""".split())


# Leaf elements cannot contain nested block-level content.
html_leaf_tags = set("""
    dt h1 h2 h3 h4 h5 h6 p title
    a abbr acronyn audio b bdi bdo big button canvas cite code data datalist
    del dfn em i iframe ins kbd label map mark meter noscript
    object output picture progress q ruby s samp select slot small span
    strong sub sup svg template textarea time u tt var video
""".split())


# Raw elements contain text which should be included in the output as-is.
html_raw_tags = set("script style".split())


# Process a tagged block.
def process(header, line_stream, meta):
    match = re.fullmatch(r':([^ ]+)([ ].+)?', header)
    tag = match.group(1)
    argstring = match.group(2) or ''
    pargs, kwargs = utils.ArgParser().parse(argstring)

    if 'raw' in pargs:
        return nodes.Node(tag, kwargs, text=str(line_stream))

    if tag in html_void_tags:
        node = nodes.Node(tag, kwargs, is_void=True)
    elif tag in html_leaf_tags:
        node = nodes.Node(tag, kwargs)
        node.children = parsers.InlineParser().parse(line_stream, meta)
    elif tag in html_raw_tags:
        node = nodes.Node(tag, kwargs, text=str(line_stream))
    else:
        node = nodes.Node(tag, kwargs)
        node.children = parsers.BlockParser().parse(line_stream, meta)

    if 'nl2lb' in pargs or 'nl2br' in pargs:
        node = nodes.LinebreakNode().append_child(node)

    return node
