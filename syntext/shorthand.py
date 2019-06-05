# ------------------------------------------------------------------------------
# Functions for processing shorthand html tags.
# ------------------------------------------------------------------------------

import html

from . import nodes
from . import parsers


# Void elements have no content or closing tag.
html_void_tags = """
    area base br col embed hr img input link meta param source track wbr
""".split()


# Leaf elements cannot contain nested block-level content.
html_leaf_tags = """
    a button dt h1 h2 h3 h4 h5 h6 label option p select span textarea time title
""".split()


# Raw elements contain text which should be included in the output as-is.
html_raw_tags = "script style".split()


# Process a tagged block.
def process(tag, pargs, kwargs, content, meta):
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
    elif tag == 'nl2lb' or tag == 'nl2br':
        node = nodes.LinebreakNode()
        node.children = parsers.BlockParser().parse(content, meta)
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
    return node

