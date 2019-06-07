# ------------------------------------------------------------------------------
# Functions for processing shorthand html tags.
# ------------------------------------------------------------------------------

import html
import re

from . import nodes
from . import parsers
from . import utils



# Void elements have no content or closing tag.
html_void_tags = """
    area base br col embed hr img input link meta param source track wbr
""".split()


# Leaf elements cannot contain nested block-level content.
html_leaf_tags = """
    dt h1 h2 h3 h4 h5 h6 p title
    a abbr acronyn audio b bdi bdo big button canvas cite code data datalist
    del dfn em i iframe ins kbd label map mark meter noscript 
    object output picture progress q ruby s samp select slot small span 
    strong sub sup svg template textarea time u tt var video 
""".split()


# Raw elements contain text which should be included in the output as-is.
html_raw_tags = "script style".split()


# Process a tagged block.
def process(header, content, meta):
    match = re.fullmatch(r':([^ ]+)([ ].+)?', header)
    tag = match.group(1)
    argstring = match.group(2) or ''
    pargs, kwargs = utils.ArgParser().parse(argstring)

    if tag == 'pre':
        text = html.escape(str(content))
        node = nodes.Node('pre', kwargs, text=text)
    elif tag == 'a':
        node = nodes.Node('a', kwargs)
        node.children = parsers.InlineParser().parse(content, meta)
        if pargs:
            node.attributes['href'] = pargs[0]
    elif tag == 'img':
        node = nodes.Node('img', kwargs, is_void=True)
        if not 'src' in kwargs:
            node.attributes['src'] = pargs[0] if pargs else ''
        if not 'alt' in kwargs:
            node.attributes['alt'] = html.escape(str(content).replace('\n', ' '))
    elif tag in html_void_tags:
        node = nodes.Node(tag, kwargs, is_void=True)
    elif tag in html_leaf_tags:
        node = nodes.Node(tag, kwargs)
        node.children = parsers.InlineParser().parse(content, meta)
    elif tag in html_raw_tags:
        node = nodes.Node(tag, kwargs, text=str(content))
    else:
        node = nodes.Node(tag, kwargs)
        node.children = parsers.BlockParser().parse(content, meta)

    if 'nl2lb' in pargs or 'nl2br' in pargs:
        node = nodes.LinebreakNode().append_child(node)
    return node

