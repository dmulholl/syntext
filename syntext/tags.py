# ------------------------------------------------------------------------------
# Functions for registering and processing generic block tags.
# ------------------------------------------------------------------------------

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
        return container_handler(tag, pargs, kwargs, content, meta)


# Default handler for 'container' elements, i.e. elements that allow nested
# block-level content. This is also the default handler for unregistered tags.
def container_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Container(tag, kwargs)
    node.children = parsers.ContainerParser().parse(content, meta)
    return node


# Default handler for 'leaf' elements, i.e. elements that do not allow nested
# block-level content. All these elements support a 'nl2br' keyword which turns
# on newline-to-linebreak mode for their content.
@register('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6')
@register('span', 'time')
@register('button', 'label', 'select', 'option', 'textarea')
def leaf_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Leaf(tag, kwargs)
    node.children = parsers.LeafParser().parse(content, meta)
    if pargs and pargs[0] in ('nl2br', '||'):
        return nodes.Nl2Br().append(node)
    return node


# Default handler for 'void' elements, i.e. elements with no closing tag and
# hence no content.
@register('hr')
def void_handler(tag, pargs, kwargs, content, meta):
    return nodes.Void(tag, kwargs)


# Default handler for 'raw' elements, i.e. elements whose content should not be
# processed any further but should be included in the output as-is.
@register('script', 'style', 'raw')
def raw_handler(tag, pargs, kwargs, content, meta):
    if tag == 'raw':
        node = nodes.Raw()
    else:
        node = nodes.Raw(tag, kwargs)
    node.append(nodes.Text(str(content)))
    return node


# Handler for the ':>>' blockquote sigil.
@register('>>')
def blockquote_tag_handler(tag, pargs, kwargs, content, meta):
    return container_handler('blockquote', pargs, kwargs, content, meta)


# Handler for the 'alert' tag and its associated sigil ':!!'
@register('alert', '!!')
def alert_tag_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Container('div', kwargs)
    node.add_class('alertbox')
    if pargs:
        for arg in pargs:
            node.add_class(arg)
    node.children = parsers.ContainerParser().parse(content, meta)
    return node


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


# Handler for the 'a' tag. The first keyword argument is used as the link url.
@register('a')
def a_tag_handler(tag, pargs, kwargs, content, meta):
    if pargs:
        kwargs['href'] = pargs[0]
    node = nodes.Leaf('a', kwargs)
    node.children = parsers.LeafParser().parse(content, meta)
    return node


# Handler for the 'null' tag and its associated sigil ':<<'.
# A null block passes its attributes on to each of its top-level children.
@register('null', '<<')
def null_tag_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Node()
    node.children = parsers.ContainerParser().parse(content, meta)

    classes = kwargs.pop('class', []).split()
    for child in node.children:
        atts = kwargs.copy()
        atts.update(child.atts)
        child.atts = atts
        for cssclass in classes:
            child.add_class(cssclass)

    return node


# Handler for the 'ignore' tag. This tag provides a commenting mechanism.
# Nested content will be omitted from the output.
@register('ignore')
def ignore_tag_handler(tag, pargs, kwargs, content, meta):
    return None


# Handler for the 'comment' tag. This tag inserts a HTML comment into the
# output.
@register('comment', 'htmlcomment')
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

    text = html.escape(text)
    pre.append(nodes.Text(text))
    return pre


# Handler for the 'nl2br' tag and its associated sigil ':||'.
# This tag turns on newline-to-linebreak mode for nested content.
@register('nl2br', '||')
def nl2lb_tag_handler(tag, pargs, kwargs, content, meta):
    node = nodes.Nl2Br()
    node.children = parsers.ContainerParser().parse(content, meta)
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


# Handler for the 'input' tag.
@register('input')
def input_tag_handler(tag, pargs, kwargs, content, meta):
    if pargs:
        kwargs['type'] = pargs[0]
    return nodes.Void(tag, kwargs)


# Handler for the 'footnote' tag.
@register('footnote')
def footnote_handler(tag, pargs, kwargs, content, meta):

    # Autogenerate a footnote index if the user hasn't specified one.
    ref = pargs[0] if pargs else ''
    if not ref:
        ref = str(meta.setdefault('footnote-index', 1))
        meta['footnote-index'] += 1

    # Wrap each footnote in a div.
    footnote = nodes.Container(
        'div',
        {'class': 'footnote', 'id': 'footnote-%s' % ref}
    )

    # Generate a backlink node.
    link = nodes.Leaf('a', {'href': '#footnote-ref-%s' % ref})
    link.append(nodes.Text(ref))

    # Generate a div node for the footnote index.
    index = nodes.Container('div', {'class': 'footnote-index'})
    index.append(link)
    footnote.append(index)

    # Generate a div node containing the parsed footnote body.
    body = nodes.Container('div', {'class': 'footnote-body'})
    body.children = parsers.ContainerParser().parse(content, meta)
    footnote.append(body)

    # Generate a footnotes div node if we haven't done so already.
    if not 'footnotes' in meta:
        meta['footnotes'] = nodes.Container('div', {'class': 'footnotes'})

    meta['footnotes'].append(footnote)
    return None
