# ------------------------------------------------------------------------------
# Functions for registering and processing tags.
# ------------------------------------------------------------------------------

import html
import re

from . import nodes
from . import parsers
from . import utils


# Use the Pygments module for syntax highlighting, if it's available.
try:
    import pygments
    import pygments.lexers
    import pygments.formatters
except ImportError:
    pygments = None


# Map tags to registered handler functions.
tagmap = {}


# Decorator function for registering tag handlers.
def register(*tags):

    def register_tag_handler(func):
        for tag in tags:
            tagmap[tag] = func
        return func

    return register_tag_handler


# Process a tag.
def process(tag, pargs, kwargs, line_stream, meta):
    if tag in tagmap:
        node = tagmap[tag](tag, pargs, kwargs, line_stream, meta)
    elif tag == 'hr' or re.fullmatch(r'-+', tag):
        node = nodes.Node('hr', kwargs, is_void=True)
    else:
        raise utils.SyntextError("Unrecognized tag '%s'." % tag)

    if 'nl2lb' in pargs or 'nl2br' in pargs:
        node = nodes.LinebreakNode().append_child(node)
    return node


# Handler for the 'div' tag - useful as a test for tags with block-level content.
@register('div')
def div_tag_handler(tag, pargs, kwargs, line_stream, meta):
    node = nodes.Node('div', kwargs)
    node.children = parsers.BlockParser().parse(line_stream, meta)
    return node


# Handler for the 'span' tag - useful as a test for tags with inline-level content.
@register('span')
def span_tag_handler(tag, pargs, kwargs, line_stream, meta):
    node = nodes.Node('span', kwargs)
    node.children = parsers.InlineParser().parse(line_stream, meta)
    return node


# Handler for the 'link' tag. Uses the first keyword argument as the url.
@register('link')
def link_tag_handler(tag, pargs, kwargs, line_stream, meta):
    node = nodes.Node('a', kwargs)
    node.children = parsers.InlineParser().parse(line_stream, meta)
    if not 'href' in kwargs:
        node.attributes['href'] = pargs[0] if pargs else ''
    return node


# Handler for blockquotes.
@register('quote')
def quote_tag_handler(tag, pargs, kwargs, line_stream, meta):
    quote = nodes.Node('blockquote', kwargs)
    quote.children = parsers.BlockParser().parse(line_stream, meta)
    if pargs:
        caption = nodes.Node('p')
        caption.add_class('blockquote-caption')
        caption.append_child(nodes.TextNode(pargs[0]))
        wrapper = nodes.Node()
        wrapper.append_child(quote)
        wrapper.append_child(caption)
        return wrapper
    return quote


# Handler for infobox tags. Supports alertbox as deprecated alias.
@register('infobox', 'alertbox')
def infobox_tag_handler(tag, pargs, kwargs, line_stream, meta):
    node = nodes.Node('div', kwargs)
    node.add_class(tag)
    node.children = parsers.BlockParser().parse(line_stream, meta)
    return node


# Handler for image tags. Uses the first keyword argument as the src.
@register('image', '!image')
def image_tag_handler(tag, pargs, kwargs, line_stream, meta):
    image = nodes.Node('img', is_void=True)
    image.attributes['src'] = pargs[0] if pargs else ''
    outernode = image

    if line_stream.has_next() and line_stream.peek().startswith('[') and line_stream.peek().endswith(']'):
        image.attributes['alt'] = html.escape(line_stream.next()[1:-1])

    if tag == '!image':
        link = nodes.Node('a')
        link.attributes['href'] = pargs[0] if pargs else ''
        link.append_child(image)
        outernode = link

    if line_stream.has_next():
        figcaption = nodes.Node('figcaption')
        figcaption.append_child(nodes.TextNode(str(line_stream).strip()))
        figure = nodes.Node('figure')
        figure.append_child(outernode)
        figure.append_child(figcaption)
        outernode = figure

    outernode.attributes.update(kwargs)
    return outernode


# Handler for the 'comment' tag; creates a HTML comment.
@register('comment')
def comment_tag_handler(tag, pargs, kwargs, line_stream, meta):
    return nodes.CommentNode(text=str(line_stream.indent(4)))


# Handler for the 'raw' tag.
@register('raw')
def raw_tag_handler(tag, pargs, kwargs, line_stream, meta):
    return nodes.Node(text=str(line_stream))


# Handler for code samples.
@register('code')
def code_tag_handler(tag, pargs, kwargs, line_stream, meta):
    node = nodes.Node('pre', kwargs)
    lang = pargs[0] if pargs else None
    text = str(line_stream)

    if lang:
        node.attributes['data-lang'] = lang
        node.add_class('lang-%s' % lang)

    if meta.get('pygmentize') and pygments and lang:
        try:
            lexer = pygments.lexers.get_lexer_by_name(lang)
        except pygments.util.ClassNotFound:
            try:
                lexer = pygments.lexers.guess_lexer(text)
            except pygments.util.ClassNotFound:
                lexer = None
        if lexer:
            node.add_class('pygments')
            formatter = pygments.formatters.HtmlFormatter(nowrap=True)
            node.text = pygments.highlight(text, lexer, formatter).strip('\n')
            return node

    node.text = html.escape(text, quote=False)
    return node


# Handler for the 'insert' tag. This tag is used to insert generated elements,
# e.g. a table of contents or block of footnotes.
@register('insert')
def insert_tag_handler(tag, pargs, kwargs, line_stream, meta):
    node = nodes.InsertNode()
    node.text = pargs[0] if pargs else ''
    return node


# Handler for the 'table' tag.
@register('table')
def table_tag_handler(tag, pargs, kwargs, line_stream, meta):

    # Strip any outer pipes and discard any blank lines.
    lines = [line.strip('|') for line in line_stream.lines if line]

    # Check for a line with colons specifying cell alignment.
    alignment = []
    for line in lines:
        match = re.fullmatch(r'[ |-]*[:][ |:-]*', line)
        if match:
            for cell in [cell.strip() for cell in line.split('|')]:
                if cell.startswith(':') and cell.endswith(':'):
                    alignment.append('center')
                elif cell.startswith(':'):
                    alignment.append('left')
                elif cell.endswith(':'):
                    alignment.append('right')
                else:
                    alignment.append(None)
            break

    # If we have a decorative top line, strip it.
    if lines and re.fullmatch(r'[ |:-]+', lines[0]):
        lines.pop(0)

    # If we have a decorative bottom line, strip it.
    if lines and re.fullmatch(r'[ |:-]+', lines[-1]):
        lines.pop()

    # Do we have a header?
    header = None
    if len(lines) > 2 and re.fullmatch(r'[ |:-]+', lines[1]):
        header = [cell.strip() for cell in lines[0].split('|')]
        lines = lines[2:]

    # Do we have a footer?
    footer = None
    if len(lines) > 2 and re.fullmatch(r'[ |:-]+', lines[-2]):
        footer = [cell.strip() for cell in lines[-1].split('|')]
        lines = lines[:-2]

    # Assemble the table body.
    body = [[cell.strip() for cell in line.split('|')] for line in lines]

    # Make a row of cells using the specified tag.
    def make_row(cells, tag):
        tr = nodes.Node('tr')
        for index, text in enumerate(cells):
            cell = nodes.Node(tag)
            cell.append_child(nodes.TextNode(text))
            if len(alignment) > index and alignment[index]:
                cell.add_class(alignment[index])
            tr.append_child(cell)
        return tr

    # Assemble the table node.
    table = nodes.Node('table', kwargs)

    if header:
        thead = nodes.Node('thead')
        thead.append_child(make_row(header, 'th'))
        table.append_child(thead)

    if footer:
        tfoot = nodes.Node('tfoot')
        tfoot.append_child(make_row(footer, 'th'))
        table.append_child(tfoot)

    tbody = nodes.Node('tbody')
    for row in body:
        tbody.append_child(make_row(row, 'td'))
    table.append_child(tbody)

    return table


# Handler for the 'footnote' tag.
@register('footnote')
def footnote_tag_handler(tag, pargs, kwargs, line_stream, meta):

    # Autogenerate a footnote index if the user hasn't specified one.
    ref = pargs[0] if pargs else ''
    if not ref:
        ref = str(meta.setdefault('footnote-index', 1))
        meta['footnote-index'] += 1

    # Wrap each footnote in a <div>.
    footnote = nodes.Node('div', {'id': 'fn:%s' % ref})

    # Generate a backlink node.
    link = nodes.Node('a', {'href': '#fnref:%s' % ref})
    link.append_child(nodes.TextNode(ref))

    # Generate a <dt> node for the footnote index.
    index = nodes.Node('dt')
    index.append_child(link)
    footnote.append_child(index)

    # Generate a <dd> node containing the parsed footnote body.
    body = nodes.Node('dd')
    body.children = parsers.BlockParser().parse(line_stream, meta)
    footnote.append_child(body)

    # Generate a footnotes <dl> node if we haven't done so already.
    if not 'footnotes' in meta:
        meta['footnotes'] = nodes.Node('dl', {'class': 'footnotes'})

    meta['footnotes'].append_child(footnote)
    return None
