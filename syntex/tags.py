# -------------------------------------------------------------------------
# Functions for registering and processing generic block tags.
# -------------------------------------------------------------------------

import html
import re

from . import nodes
from . import parsers
from . import escapes


# Use the Pygments module for syntax highlighting, if it's available.
try:
    import pygments
    import pygments.lexers
    import pygments.formatters
except ImportError:
    pygments = None


# Maps tags to registered handler functions.
tagmap = {}


# Decorator function for registering tag handlers.
def register(*tags):

    def register_tag_handler(func):
        for tag in tags:
            tagmap[tag] = func
        return func

    return register_tag_handler


# Entry point.
def process(tag, pargs, kwargs, content, meta):
    if tag in tagmap:
        return tagmap[tag](tag, pargs, kwargs, content, meta)
    else:
        return container_block_handler(tag, pargs, kwargs, content, meta)


# Handler for block-level elements that allow nested blocks. This is the
# default handler for unregistered tags.
def container_block_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Container(tag, kwargs)
    node.children = parsers.BlockParser().parse(content, meta)
    return node


# Handler for block-level elements that do not allow nested block.
@register('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6')
def leaf_block_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Leaf(tag, kwargs)
    node.append(nodes.Text(str(content)))
    return node


# Hander for block-level elements with raw text content.
@register('script', 'style')
def raw_block_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Raw(tag, kwargs)
    node.append(nodes.Text(str(content)))
    return node


# Handler for the 'esc' tag. Includes content in its raw state.
@register('esc', escapes.char2esc['\\'])
def esc_tag_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Raw()
    node.append(nodes.Text(str(content)))
    return node


# Handler for the ':>>' blockquote sigil.
@register('>>')
def blockquote_tag_handler(tag, pargs, kwargs, content, meta):
    return container_block_handler('blockquote', pargs, kwargs, content, meta)


# Handler for the 'alert' tag and its associated sigil ':!!'
@register('alert', '!!')
def alert_tag_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Container('div', kwargs)
    node.add_class('stx-alert')
    if pargs:
        for arg in pargs:
            node.add_class('stx-%s' % arg)
    node.children = parsers.BlockParser().parse(content, meta)
    return node


# Handler for the 'hr' tag. Horizontal rules are void elements and do not
# support content of any sort.
@register('hr')
def hr_tag_handler(tag, pargs, kwargs, content, meta):
    return nodes.Void('hr', kwargs)


# Handler for the 'input' tag. Input elements are void and cannot contain
# content of any sort.
@register('input')
def input_tag_handler(tag, pargs, kwargs, content, meta):
    return nodes.Void('input', kwargs)


# Handler for the 'img' tag. The first keyword is used as the src attribute;
# the block's content is used as the alt text. If a second keyword url is
# supplied, the image element is wrapped in a link pointing to the url.
@register('img')
def img_tag_handler(tag, pargs, kwargs, content, meta):
    if len(pargs) > 1:
        kwargs['href'] = pargs[1]
        link = nodes.Leaf('a', kwargs)
        image = nodes.Void('img')
        link.append(image)
    else:
        link = None
        image = nodes.Void('img', kwargs)

    if not 'src' in image.atts:
        image.atts['src'] = pargs[0] if pargs else ''
    if not 'alt' in image.atts:
        image.atts['alt'] = html.escape(str(content).replace('\n', ' '))

    return link or image


# Handler for the 'null' tag and its associated sigil ':<<'.
# A null block passes its attributes on to each of its top-level children.
@register('null', '<<')
def null_tag_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Node()
    node.children = parsers.BlockParser().parse(content, meta)

    classes = kwargs.pop('class', []).split()
    for child in node.children:
        atts = kwargs.copy()
        atts.update(child.atts)
        child.atts = atts
        for cssclass in classes:
            child.add_class(cssclass)

    return node


# Handler for the 'ignore' tag and its associated sigil '://'. This tag
# provides a commenting mechanism. Nested content will be omitted from the
# output.
@register('ignore', '//')
def ignore_tag_handler(tag, pargs, kwargs, content, meta):
    return True


# Handler for the 'comment' tag and its associated sigil ':##'. This tag
# inserts a HTML comment into the output.
@register('comment', '##')
def html_comment_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Comment()
    node.append(nodes.Text(str(content.indent(4))))
    return node


# Handler for the 'pre' tag and its associated sigil ':::'.
@register('pre', '::')
def pre_tag_handler(tag, pargs, kwargs, content, meta):
    pre = nodes.Raw('pre', kwargs)
    lang = pargs[0] if pargs else None
    text = str(content)

    if lang:
        pre.atts['data-lang'] = lang
        pre.add_class('lang-%s' % lang)

    if meta.get('pygmentize') and pygments and lang:
        try:
            lexer = pygments.lexers.get_lexer_by_name(lang)
        except pygments.util.ClassNotFound:
            try:
                lexer = pygments.lexers.guess_lexer(text)
            except pygments.util.ClassNotFound:
                lexer = None
        if lexer:
            pre.add_class('pygments')
            formatter = pygments.formatters.HtmlFormatter(nowrap=True)
            text = pygments.highlight(text, lexer, formatter).strip('\n')
            pre.append(nodes.Text(text))
            return pre

    text = html.escape(text, False)
    pre.append(nodes.Text(text))
    return pre


# Handler for the 'nl2br' tag and its associated sigil ':||'.
# This tag turns on newline-to-linebreak mode for nested content.
@register('nl2br', '||')
def nl2lb_tag_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Nl2Br()
    node.children = parsers.BlockParser().parse(content, meta)
    return node


# Handler for the 'insert' tag. This tag is used to insert generated elements,
# e.g. a table of contents or block of footnotes.
@register('insert')
def insert_tag_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Insert()
    node.content = pargs[0] if pargs else ''
    return node


# Handler for the ':++' table sigil.
@register('++')
def table_handler(tag, pargs, kwargs, content, meta):

    # Strip any outer pipes and discard any blank lines.
    lines = [line.strip('|') for line in content.lines if line]

    # Check for a line with colons specifying cell alignment.
    alignment = []
    for line in lines:
        match = re.fullmatch(r'[ |-]*[:][ |:-]*', line)
        if match:
            for cell in [cell.strip() for cell in line.split('|')]:
                if cell.startswith(':') and cell.endswith(':'):
                    alignment.append('stx-center')
                elif cell.startswith(':'):
                    alignment.append('stx-left')
                elif cell.endswith(':'):
                    alignment.append('stx-right')
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
        tr = nodes.Container('tr')
        for index, text in enumerate(cells):
            cell = nodes.Container(tag)
            cell.append(nodes.Text(text))
            if len(alignment) > index and alignment[index]:
                cell.add_class(alignment[index])
            tr.append(cell)
        return tr

    # Assemble the table node.
    table = nodes.Container('table', kwargs)

    if header:
        thead = nodes.Container('thead')
        thead.append(make_row(header, 'th'))
        table.append(thead)

    if footer:
        tfoot = nodes.Container('tfoot')
        tfoot.append(make_row(footer, 'th'))
        table.append(tfoot)

    tbody = nodes.Container('tbody')
    for row in body:
        tbody.append(make_row(row, 'td'))
    table.append(tbody)

    return table
