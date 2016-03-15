#!/usr/bin/env python3
"""
Syntex
======

A lightweight, markdownish markup language for generating HTML.

To use as a script:

    $ syntex.py < input.txt > output.html

To use as a library module:

    import syntex
    html = syntex.render(text)

Author: Darren Mulholland <darren@mulholland.xyz>
License: Public Domain

"""

import sys
import re
import os
import collections
import hashlib
import unicodedata
import argparse
import pprint
import textwrap
import html


# Use the Pygments module for syntax highlighting, if available.
try:
    import pygments
    import pygments.lexers
    import pygments.formatters
except ImportError:
    pygments = None


# Library version number.
__version__ = "0.11.0.dev"


# Pygmentize flag. Set to true to add syntax highlighting to code samples.
pygmentize = False


# The following characters can be escaped with a backslash.
ESCCHARS = '\\*:`[]#=-!().•'


# Placeholders to substitute for escaped characters during preprocessing.
STX = '\x02'
ETX = '\x03'
ESCBS = 'esc%s%s%s' % (STX, ord('\\'), ETX)
ESCMAP = {'esc%s%s%s' % (STX, ord(c), ETX): c for c in ESCCHARS}


# Stores registered tag handler functions indexed by tag name.
tagmap = {}


# -------------------------------------------------------------------------
# AST Nodes
# -------------------------------------------------------------------------


class Node:

    """ Input text is parsed into a Node tree. """

    def __init__(self, tag, attrs=None, meta=''):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = []
        self.meta = meta
        self.text = ''

    def __iter__(self):
        for child in self.children:
            yield child

    def __repr__(self):
        return self.repr()

    def repr(self, depth=0):
        output = "·  " * depth + self.get_tag()
        if self.text:
            text = repr(self.text)
            if len(text) < 40:
                output += " " + text
            else:
                output += " " + text[:18] + "..." + text[-18:]
        if self.meta:
            output += " meta=" + repr(self.meta)
        output += '\n'
        for child in self.children:
            output += child.repr(depth + 1)
        return output

    def get_tag(self, alt='', close=False):
        tag = alt or self.tag
        slash = '/' if close else ''
        attrs = ''.join(
            ' %s="%s"' % (key, self.attrs[key]) for key in sorted(self.attrs)
        )
        return '<%s%s%s>' % (tag, attrs, slash)

    def get_text(self):
        if self.text:
            return self.text
        else:
            return ''.join(child.get_text() for child in self.children)

    def append(self, node):
        self.children.append(node)
        return node

    def add_class(self, newclass):
        classes = self.attrs.get('class', '').split()
        if not newclass in classes:
            classes.append(newclass)
            self.attrs['class'] = ' '.join(sorted(classes))


class Text(Node):

    """ A Text node contains only text content and has no child nodes. """

    def __init__(self, text):
        Node.__init__(self, 'text')
        self.text = text


# -------------------------------------------------------------------------
# Text Processors
# -------------------------------------------------------------------------


class ParagraphProcessor:

    """ Consumes a sequence of consecutive non-empty lines. """

    regex = re.compile(r"(^[ ]*[^ \n]+.*\n)+", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        node = Node('p')
        node.append(Text(strip(match.group(0))))
        return True, node, match.end(0)


class CodeProcessor:

    """ Consumes a sequence of consecutive indented or empty lines. """

    regex = re.compile(r"""
        ^[ ]{4}[^ \n]+.*\n
        (
            (^[ ]*\n)
            |
            (^[ ]{4}.+\n)
        )*
    """, re.VERBOSE | re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        node = Node('pre', meta='rawtext')
        text = esc(match.group(0), False)
        node.append(Text(dedent(strip(text))))
        return True, node, match.end(0)


class H1Processor:

    """ Consumes a H1 heading of the form:

        =======
        Heading
        =======

    The first line of '=' is optional.

    """

    regex = re.compile(r"""
        (?:^=+[ ]*\n)?
        ^(.+)\n
        ^=+[ ]*\n
    """, re.VERBOSE | re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        node = Node('h1')
        node.append(Text(match.group(1).strip()))
        return True, node, match.end(0)


class H2Processor:

    """ Consumes a H2 heading of the form:

        -------
        Heading
        -------

    The first line of '-' is optional.

    """

    regex = re.compile(r"""
        (?:^-+[ ]*\n)?
        ^(.+)\n
        ^-+[ ]*\n
    """, re.VERBOSE | re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        node = Node('h2')
        node.append(Text(match.group(1).strip()))
        return True, node, match.end(0)


class HeadingProcessor:

    """ Consumes an arbitrary level heading of the form:

        ### Heading ###

    The number of leading '#' specifies the heading level.
    Trailing '#' are optional.

    """

    regex = re.compile(r"^([#]{1,6})(.+?)[#]*\n", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        tag = 'h' + str(len(match.group(1)))
        node = Node(tag)
        node.append(Text(match.group(2).strip()))
        return True, node, match.end(0)


class EmptyLineProcessor:

    """ Skips over blank lines. """

    regex = re.compile(r"(^[ ]*\n)+", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        return True, None, match.end(0)


class SkipLineProcessor:

    """ Skips over a single line. """

    regex = re.compile(r"^.*\n", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        return True, None, match.end(0)


class TextProcessor:

    """ Consumes a single non-empty line of text. """

    regex = re.compile(r"^[ ]*[^ \n]+.*\n", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        return True, Text(match.group(0)), match.end(0)


class HorizontalRuleProcessor:

    """ Consumes a line containing three or more '-' or '*' characters.

    The characters may optionally be separated by spaces.

    """

    regex = re.compile(r"^[ ]{0,3}([-*])[ ]*\1[ ]*\1.*\n", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        return True, Node('hr'), match.end(0)


class UnorderedListProcessor:

    """ Consumes an unordered list.

    The list item marker is one of (*, •, -, or +).

    Each list item consists of its opening line plus all subsequent blank
    or indented lines. List item markers can be indented by up to three
    spaces.

    Example:

        * foo
        * bar
        * baz

    Switching to a different list item marker starts a new list.

    """

    item = r"""
        ^[ ]{0,3}[%s](\n|(?:[ ].*\n))
        ((
            (^[ ]*\n)
            |
            (^[ ]+.+\n)
        )*)
    """

    regexes = []
    re_blankline = re.compile(r"^[ ]*\n", re.MULTILINE)

    def __init__(self):
        for marker in '*•-+':
            item = self.item % marker
            re_item = re.compile(item, re.VERBOSE | re.MULTILINE)
            re_list = re.compile('(%s)+' % item, re.VERBOSE | re.MULTILINE)
            self.regexes.append((re_item, re_list))

    def __call__(self, text, pos):
        for re_item, re_list in self.regexes:
            list_match = re_list.match(text, pos)
            if not list_match:
                continue

            if self.re_blankline.search(list_match.group(0).strip()):
                meta = 'block'
                processors = ()
            else:
                meta = 'compact'
                processors = ('empty', 'ul', 'ol', 'text')

            ul = Node('ul', meta=meta)
            for item_match in re_item.finditer(list_match.group(0)):
                head = item_match.group(1).lstrip(' ')
                body = item_match.group(2)
                content = head + dedent(body)
                li = ul.append(Node('li', meta=meta))
                li.children = BlockParser(*processors).parse(content)
            return True, ul, list_match.end(0)

        return False, None, pos


class OrderedListProcessor:

    """ Consumes an ordered list. The list item marker is '#.' or '<int>.'.

    Each list item consists of its opening line plus all subsequent blank
    or indented lines. List item markers can be indented by up to three
    spaces.

    Example:

        1. foo
        2. bar
        3. baz

    Changing to a different list item marker starts a new list.

    """

    item = r"""
        ^[ ]{0,3}(%s)(\n|(?:[ ].*\n))
        ((
            (^[ ]*\n)
            |
            (^[ ]+.+\n)
        )*)
    """

    regexes = []
    re_blankline = re.compile(r"^[ ]*\n", re.MULTILINE)

    def __init__(self):
        for marker in (r'\#\.', r'\d+\.'):
            item = self.item % marker
            re_item = re.compile(item, re.VERBOSE | re.MULTILINE)
            re_list = re.compile('(%s)+' % item, re.VERBOSE | re.MULTILINE)
            self.regexes.append((re_item, re_list))

    def __call__(self, text, pos):
        for re_item, re_list in self.regexes:
            first_item_match = re_item.match(text, pos)
            if not first_item_match:
                continue

            list_match = re_list.match(text, pos)
            if self.re_blankline.search(list_match.group(0).strip()):
                meta = 'block'
                processors = ()
            else:
                meta = 'compact'
                processors = ('empty', 'ul', 'ol', 'text')

            start = first_item_match.group(1).rstrip('.')
            if start in ('#', '1'):
                ol = Node('ol', meta=meta)
            else:
                ol = Node('ol', {'start': start}, meta=meta)

            for item_match in re_item.finditer(list_match.group(0)):
                head = item_match.group(2).lstrip(' ')
                body = item_match.group(3)
                content = head + dedent(body)
                li = ol.append(Node('li', meta=meta))
                li.children = BlockParser(*processors).parse(content)
            return True, ol, list_match.end(0)

        return False, None, pos


class DefinitionListProcessor:

    """ Consumes a definition list of the form:

        ~ Term 1

            This is the definition of the term.

        ~ Term 2

            This is the definition of the term.

    """

    item = r"""
        ^[ ]{0,3}[~][ ]*([^\n]+)\n
        ((
            (^[ ]*\n)
            |
            (^[ ]+.+\n)
        )*)
    """

    re_item = re.compile(item, re.VERBOSE | re.MULTILINE)
    re_list = re.compile(r"(%s)+" % item, re.VERBOSE | re.MULTILINE)

    def __call__(self, text, pos):
        list_match = self.re_list.match(text, pos)
        if not list_match:
            return False, None, pos
        dl = Node('dl')
        for item_match in self.re_item.finditer(list_match.group(0)):
            dt = dl.append(Node('dt'))
            dt.append(Text(item_match.group(1).strip()))
            dd = dl.append(Node('dd'))
            dd.children = BlockParser().parse(dedent(item_match.group(2)))
        return True, dl, list_match.end(0)


class HtmlProcessor:

    """ Consumes a block of raw HTML. """

    regex = re.compile(r"""
        ^<(\w+)[^>]*>
        .*?
        ^</\1>[ ]*\n
    """, re.VERBOSE | re.MULTILINE | re.DOTALL)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        node = Node('esc', meta='rawtext')
        node.append(Text(match.group(0).strip()))
        return True, node, match.end(0)


class GenericBlockProcessor:

    """ Consumes a generic block of the form:

        :tag [keyword] [.class1 .class2] [#id] [attr1=foo attr2="bar"]
            block content
            block content

            block content
            ...

    The block's content consists of all consecutive blank or indented lines
    following the block header. How this content is processed depends on
    the tag; in the general case content is processed recursively and can
    contain nested block-level structures.

    """

    block_regex = re.compile(r"""
        ^:([^ \n]+)([ ]+.+)?[ ]*\n
        ((
            (^[ ]*\n)
            |
            (^[ ]+.+\n)
        )*)
    """, re.VERBOSE | re.MULTILINE)

    args_regex = re.compile(r"""
        (?:([^\s'"=]+)=)?
        (
            "((?:[^\\"]|\\.)*)"
            |
            '((?:[^\\']|\\.)*)'
        )
        |
        ([^\s'"=]+)=(\S+)
        |
        (\S+)
    """, re.VERBOSE)

    def __call__(self, text, pos):
        match = self.block_regex.match(text, pos)
        if not match:
            return False, None, pos

        tag = match.group(1)
        content = dedent(match.group(3)) if match.group(3) else ''
        args = match.group(2).strip() if match.group(2) else ''
        pargs, kwargs = self.parse_args(args)

        # We delegate responsibility here to the registered tag handler.
        if tag in tagmap:
            node = tagmap[tag](tag, pargs, kwargs, content)
        else:
            node = default_block_handler(tag, pargs, kwargs, content)

        return True, node, match.end(0)

    def parse_args(self, argstring):
        pargs, kwargs = [], {}
        for match in self.args_regex.finditer(argstring):
            if match.group(2) or match.group(5):
                key = match.group(1) or match.group(5)
                value = match.group(3) or match.group(4) or match.group(6)
                if match.group(3) or match.group(4):
                    value = bytes(value, 'utf-8').decode('unicode_escape')
                if key:
                    kwargs[key] = value
                else:
                    pargs.append(value)
            else:
                pargs.append(match.group(7))

        classes = []
        for arg in pargs[:]:
            if arg.startswith('.'):
                classes.append(arg[1:])
                pargs.remove(arg)
            if arg.startswith('#'):
                kwargs['id'] = arg[1:]
                pargs.remove(arg)
        if 'class' in kwargs:
            classes.extend(kwargs['class'].split())
        if classes:
            kwargs['class'] = ' '.join(sorted(classes))

        return pargs, kwargs


# -------------------------------------------------------------------------
# Block Parser
# -------------------------------------------------------------------------


class BlockParser:

    """ Parses a string and returns a list of block elements.

    A BlockParser object can be initialized with a list of processors
    to use in parsing the string. The 'skipline' processor will be
    automatically appended to the end of the list to skip over lines
    that cannot be matched by any of the other specified processors.

    Adjacent text elements are automatically merged.

    """

    processor_map = collections.OrderedDict()
    processor_map['empty'] = EmptyLineProcessor()
    processor_map['block'] = GenericBlockProcessor()
    processor_map['html'] = HtmlProcessor()
    processor_map['h1'] = H1Processor()
    processor_map['h2'] = H2Processor()
    processor_map['code'] = CodeProcessor()
    processor_map['hr'] = HorizontalRuleProcessor()
    processor_map['ul'] = UnorderedListProcessor()
    processor_map['ol'] = OrderedListProcessor()
    processor_map['dl'] = DefinitionListProcessor()
    processor_map['heading'] = HeadingProcessor()
    processor_map['paragraph'] = ParagraphProcessor()
    processor_map['skipline'] = SkipLineProcessor()
    processor_map['text'] = TextProcessor()

    def __init__(self, *pargs):
        if pargs:
            self.processors = [self.processor_map[arg] for arg in pargs]
            self.processors.append(self.processor_map['skipline'])
        else:
            self.processors = list(self.processor_map.values())

    def parse(self, text):
        pos = 0
        elements = []
        if not text.endswith('\n'):
            text += '\n'
        while pos < len(text):
            for processor in self.processors:
                match, node, pos = processor(text, pos)
                if match:
                    if node:
                        if node.tag == 'text' and elements and \
                            elements[-1].tag == 'text':
                            elements[-1].text += node.text
                        else:
                            elements.append(node)
                    break
        return elements


# -------------------------------------------------------------------------
# Tag Handlers
# -------------------------------------------------------------------------


def register(*tags):

    """ Decorator function for registering tag handlers. """

    def register_tag_handler(func):
        for tag in tags:
            tagmap[tag] = func
        return func

    return register_tag_handler


# Handler for block-level elements that allow nested blocks.
def default_block_handler(tag, pargs, kwargs, content):
    node = Node(tag, kwargs)
    node.children = BlockParser().parse(content)
    return node


# Handler for block-level elements that do not allow nested blocks.
@register('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6')
def terminal_block_handler(tag, pargs, kwargs, content):
    node = Node(tag, kwargs)
    node.append(Text(strip(content)))
    return node


# Handler for block-level elements with raw text content.
@register('style', 'script')
def rawtext_handler(tag, pargs, kwargs, content):
    node = Node(tag, kwargs, meta='rawtext')
    node.append(Text(strip(content)))
    return node


# Handler for the 'esc' tag and its associated sigil ':\\'.
@register('esc', ESCBS)
def raw_handler(tag, pargs, kwargs, content):
    node = Node('esc', kwargs, meta='rawtext')
    node.append(Text(strip(content)))
    return node


# Handler for the 'blockquote' tag and its associated sigil ':>>'.
@register('blockquote', '>>')
def blockquote_handler(tag, pargs, kwargs, content):
    node = Node('blockquote', kwargs)
    node.children = BlockParser().parse(content)
    return node


# Handler for the 'pre' tag and its associated sigil ':::'. Code samples with
# a language keyword specified will have syntax highlighting applied if the
# `pygmentize` flag is set to true.
@register('pre', '::')
def code_handler(tag, pargs, kwargs, content):
    node = Node('pre', kwargs, meta='rawtext')
    lang = pargs[0] if pargs else None

    if lang:
        node.attrs['data-lang'] = lang
        node.add_class('lang-%s' % lang)

    text = esc(strip(content), False)
    if pygmentize and pygments and lang:
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
            text = strip(pygments.highlight(text, lexer, formatter))

    node.append(Text(text))
    return node


# Handler for the 'nl2br' tag and its associated sigil ':||'.
# This tag turns on newline-to-linebreak mode for nested content.
@register('nl2br', '||')
def nl2lb_handler(tag, pargs, kwargs, content):
    node = Node('nl2br')
    node.children = BlockParser().parse(content)
    return node


# Handler for the 'alert' tag and its associated sigil ':!!'
@register('alert', '!!')
def alertbox_handler(tag, pargs, kwargs, content):
    node = Node('div', kwargs)
    node.add_class('stx-alert')
    if pargs:
        for arg in pargs:
            node.add_class('stx-%s' % arg)
    node.children = BlockParser().parse(content)
    return node


# Handler for the block-level 'image' tag. The block's content is used as
# the image's alt text.
@register('image')
def image_handler(tag, pargs, kwargs, content):
    node = Node('image', kwargs)
    if not 'src' in kwargs:
        node.attrs['src'] = pargs[0] if pargs else ''
    if not 'alt' in kwargs:
        node.attrs['alt'] = esc(strip(content)).replace('\n', ' ')
    return node


# Handler for the 'null' tag and its associated sigil ':<<'.
# A null block passes its attributes on to each of its top-level children.
@register('null', '<<')
def null_handler(tag, pargs, kwargs, content):
    node = Node('null')
    node.children = BlockParser().parse(content)
    classes = kwargs.get('class', '').split()
    for child in node:
        attrs = kwargs.copy()
        attrs.update(child.attrs)
        child.attrs = attrs
        for cssclass in classes:
            child.add_class(cssclass)
    return node


# Handler for the ':insert' tag used to insert automatically-generated elements
# into a page, e.g. a table of contents.
@register('insert')
def insert_handler(tag, pargs, kwargs, content):
    node = Node('insert', kwargs)
    node.meta = pargs[0] if pargs else ''
    return node


# Handler for the ':ignore' tag and its associated sigil '://'. This tag
# provides a commenting mechanism. Nested content will be omitted from the
# output.
@register('ignore', '//')
def ignore_handler(tag, pargs, kwargs, content):
    return None


# Handler for the 'comment' tag and its associated sigil ':##'. This tag
# inserts a HTML comment into the output.
@register('comment', '##')
def html_comment_handler(tag, pargs, kwargs, content):
    node = Node('comment')
    node.append(Text(strip(content)))
    return node


# Handler for the ':++' table sigil.
@register('++')
def table_handler(tag, pargs, kwargs, content):
    lines = [line.strip(' |') for line in content.splitlines()]
    lines = [line for line in lines if line]
    if len(lines) < 3:
        return None

    head = [cell.strip() for cell in lines.pop(0).split('|')]
    meta = [cell.strip() for cell in lines.pop(0).split('|')]
    body = [[cell.strip() for cell in line.split('|')] for line in lines]

    align = [None for cell in head]
    for i, cell in enumerate(meta):
        if cell.startswith(':') and cell.endswith(':'):
            align[i] = 'stx-center'
        elif cell.startswith(':'):
            align[i] = 'stx-left'
        elif cell.endswith(':'):
            align[i] = 'stx-right'

    def make_row(cells, celltag):
        tr = Node('tr')
        for i, cell in enumerate(cells):
            el = tr.append(Node(celltag))
            if align[i]:
                el.add_class(align[i])
            el.append(Text(cell))
        return tr

    table = Node('table', kwargs)
    thead = table.append(Node('thead'))
    tbody = table.append(Node('tbody'))
    thead.append(make_row(head, 'th'))
    for row in body:
        tbody.append(make_row(row, 'td'))
    return table


# -------------------------------------------------------------------------
# Renderers
# -------------------------------------------------------------------------


class HtmlRenderer:

    """ Renders a Node tree as HTML.

        html = HtmlRenderer(link_refs, inserts).render(node)

    The constructor accepts optional dictionaries of link references and
    insertable elements to use while rendering the node tree.

    """

    # ---------------------
    # Inline Markup Regexes
    # ---------------------

    # **foo bar**
    re_strong = re.compile(r"\*{2}(\S.*?\S)\*{2}")

    # *foo bar*
    re_emphasis = re.compile(r"\*(\S.*?\S)\*")

    # `foo bar`
    re_backticks = re.compile(r"`(.+?)`")

    # [link text](url "title")
    re_link = re.compile(r"""\[([^\]]+)\]\((\S+)(?:[ ]+"([^"]*)")?\)""")

    # [link text][ref]
    re_ref_link = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")

    # ![alt text](url "title")
    re_img = re.compile(r"""!\[([^\]]*)\]\((\S+)(?:[ ]+"([^"]*)")?\)""")

    # ![alt text][ref]
    re_ref_img = re.compile(r"!\[([^\]]*)\]\[([^\]]*)\]")

    # [^ref] or [^]
    re_footnote = re.compile(r"\[\^([^\]]*)\]")

    # &amp; &#x27;
    re_entity = re.compile(r"&[#a-zA-Z0-9]+;")

    # html tags: <span>, </span>, <!-- comment -->, etc.
    re_html = re.compile(r"<([a-zA-Z/][^>]*?|!--.*?--)>")

    # <http://example.com>
    re_bracketed_url = re.compile(r"<((?:https?|ftp)://[^>]+)>")

    # http://example.com
    re_bare_url = re.compile(r"""
        (^|\s)
        (https?|ftp)
        (://[-A-Z0-9+&@#/%?=~_|\[\]\(\)!:,\.;]*[-A-Z0-9+&@#/%=~_|\[\]])
        ($|\W)
        """, re.VERBOSE | re.MULTILINE | re.IGNORECASE)

    # Set this flag to true to convert newlines to <br> tags by default.
    nl2br = False

    def __init__(self, link_refs=None, inserts=None):
        self.link_refs = link_refs or {}
        self.inserts = inserts or {}
        self.hashes = {}
        self.footnote_index = 1
        self.context = ['nl2br' if self.nl2br else '']

    def render(self, node):
        """ Renders a node, returning a string of HTML. """
        rendered = self._render(node)
        for key, value in self.hashes.items():
            rendered = rendered.replace(key, value)
        for key, value in ESCMAP.items():
            rendered = rendered.replace(key, value)
        return strip(rendered)

    def _hash(self, text):
        digest = hashlib.sha1(text.encode()).hexdigest()
        self.hashes[digest] = text
        return digest

    def _render(self, node):
        method = '_render_element_%s' % node.tag
        if hasattr(self, method):
            return getattr(self, method)(node)
        elif node.meta == 'rawtext':
            return self._render_element_rawtext(node)
        else:
            return self._render_element_default(node)

    def _render_element_default(self, node):
        html = [node.get_tag(), '\n']
        for child in node:
            html.append(self._render(child))
        html.append('</%s>\n' % node.tag)
        return ''.join(html)

    def _render_element_rawtext(self, node):
        html = [node.get_tag(), '\n', node.get_text(), '\n']
        html.append('</%s>\n' % node.tag)
        return ''.join(html)

    def _render_element_root(self, node):
        return ''.join(self._render(child) for child in node)

    def _render_element_null(self, node):
        return ''.join(self._render(child) for child in node)

    def _render_element_image(self, node):
        return node.get_tag('img', close=True) + '\n'

    def _render_element_hr(self, node):
        return node.get_tag() + '\n'

    def _render_element_insert(self, node):
        if node.meta in self.inserts:
            insert = self.inserts[node.meta]
            insert.attrs.update(node.attrs)
            return self._render(insert)
        else:
            return ''

    def _render_element_footnotes(self, node):
        html = [node.get_tag('dl'), '\n']
        for fnote in node:
            html.append('<dt id="fn-%s">\n%s\n</dt>\n' % (fnote.meta, fnote.meta))
            html.append('<dd>\n')
            for child in fnote:
                html.append(self._render(child))
            html.append('</dd>\n')
        html.append('</dl>\n')
        return ''.join(html)

    def _render_element_esc(self, node):
        return strip(node.get_text()) + '\n'

    def _render_element_comment(self, node):
        html = ['<!--\n']
        html.append(indent(node.get_text()))
        html.append('\n-->\n')
        return ''.join(html)

    def _render_element_nl2br(self, node):
        self.context.append('nl2br')
        html = ''.join(self._render(child) for child in node)
        self.context.pop()
        return html

    def _render_element_text(self, node):
        text = node.text
        text = self._render_inline_backticks(text)
        text = self._render_inline_bracketed_urls(text)
        text = self._render_inline_html(text)
        text = self._render_inline_entities(text)
        text = esc(text, False)
        text = self._render_inline_strong(text)
        text = self._render_inline_emphasis(text)
        text = self._render_inline_images(text)
        text = self._render_inline_ref_images(text)
        text = self._render_inline_links(text)
        text = self._render_inline_ref_links(text)
        text = self._render_inline_footnotes(text)
        # text = self._do_inline_bare_urls(text)
        text = text.rstrip('\n')
        if 'nl2br' in self.context:
            text = text.replace('\n', '<br>\n')
        return text + '\n'

    def _render_inline_html(self, text):
        return self.re_html.sub(lambda m: self._hash(m.group()), text)

    def _render_inline_entities(self, text):
        return self.re_entity.sub(lambda m: self._hash(m.group()), text)

    def _render_inline_strong(self, text):
        return self.re_strong.sub(r"<strong>\1</strong>", text)

    def _render_inline_emphasis(self, text):
        return self.re_emphasis.sub(r"<em>\1</em>", text)

    def _render_inline_bracketed_urls(self, text):
        return self.re_bracketed_url.sub(r'<a href="\1">\1</a>', text)

    def _render_inline_bare_urls(self, text):
        return self.re_bare_url.sub(r'\1<a href="\2\3">\2\3</a>\4', text)

    def _render_inline_backticks(self, text):
        def callback(match):
            return self._hash('<code>%s</code>' % esc(match.group(1), False))
        return self.re_backticks.sub(callback, text)

    def _render_inline_images(self, text):
        def callback(match):
            alt = esc(match.group(1))
            url = match.group(2)
            title = esc(match.group(3) or '')
            if title:
                return '<img src="%s" alt="%s" title="%s"/>' % (url, alt, title)
            else:
                return '<img src="%s" alt="%s"/>' % (url, alt)
        return self.re_img.sub(callback, text)

    def _render_inline_ref_images(self, text):
        def callback(match):
            alt = match.group(1)
            ref = match.group(2).lower() if match.group(2) else alt.lower()
            url, title = self.link_refs.get(ref, ('', ''))
            if title:
                return '<img src="%s" alt="%s" title="%s"/>' % (
                    url, esc(alt), esc(title)
                )
            else:
                return '<img src="%s" alt="%s"/>' % (url, esc(alt))
        return self.re_ref_img.sub(callback, text)

    def _render_inline_links(self, text):
        def callback(match):
            text = match.group(1)
            url = match.group(2)
            title = esc(match.group(3) or '')
            if title:
                return '<a href="%s" title="%s">%s</a>' % (url, title, text)
            else:
                return '<a href="%s">%s</a>' % (url, text)
        return self.re_link.sub(callback, text)

    def _render_inline_ref_links(self, text):
        def callback(match):
            text = match.group(1)
            ref = match.group(2).lower() if match.group(2) else text.lower()
            url, title = self.link_refs.get(ref, ('#', ''))
            if title:
                return '<a href="%s" title="%s">%s</a>' % (url, esc(title), text)
            else:
                return '<a href="%s">%s</a>' % (url, text)
        return self.re_ref_link.sub(callback, text)

    def _render_inline_footnotes(self, text):
        def callback(match):
            if match.group(1):
                ref = match.group(1)
            else:
                ref = self.footnote_index
                self.footnote_index += 1
            return '<sup class="fn-ref"><a href="#fn-%s">%s</a></sup>' % (ref, ref)
        return self.re_footnote.sub(callback, text)


# -------------------------------------------------------------------------
# Table of Contents Builder
# -------------------------------------------------------------------------


class TOCBuilder:

    """ Table of Contents Builder

    Processes a tree of block elements to produce a table of contents
    with links to each heading in the document. Note that this process
    modifies the tree in place by adding an automatically generated ID
    to any heading element that lacks one.

    The table is returned as a Node tree representing an unordered
    list with nested sublists.

        toc = TOCBuilder(doctree).toc()

    """

    def __init__(self, tree):
        self.renderer = HtmlRenderer()
        self.root = dict(level=0, text='ROOT', id='', subs=[])
        self.stack = [self.root]
        self.ids = []
        self._process_element(tree)

    def _process_element(self, node):
        if node.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            heading = self._make_heading_node(node)
            while heading['level'] <= self.stack[-1]['level']:
                self.stack.pop()
            self.stack[-1]['subs'].append(heading)
            self.stack.append(heading)
        else:
            for child in node:
                self._process_element(child)

    def _make_heading_node(self, node):
        level = int(node.tag[1])
        html = self.renderer.render(node)
        text = strip_tags(html).strip()
        if 'id' in node.attrs:
            id = node.attrs['id']
        else:
            index = 2
            slug = idify(text)
            id = slug
            while id in self.ids:
                id = '%s-%s' % (slug, index)
                index += 1
            node.attrs['id'] = id
        self.ids.append(id)
        return dict(level=level, text=text, id=id, subs=[])

    def toc(self):
        """ Skips over root-level H1 headings. """
        ul = Node('ul', {'class': 'stx-toc'}, meta='compact')
        for node in self.root['subs']:
            if node['level'] == 1:
                for subnode in node['subs']:
                    ul.append(self._make_li_element(subnode))
            else:
                ul.append(self._make_li_element(node))
        return ul

    def fulltoc(self):
        """ Includes root-level H1 headings. """
        ul = Node('ul', {'class': 'stx-toc'}, meta='compact')
        for node in self.root['subs']:
            ul.append(self._make_li_element(node))
        return ul

    def _make_li_element(self, node):
        li = Node('li', meta='compact')
        li.append(Text('[%s](#%s)' % (node['text'], node['id'])))
        if node['subs']:
            ul = li.append(Node('ul', meta='compact'))
            for child in node['subs']:
                ul.append(self._make_li_element(child))
        return li

    def nodes(self):
        """ Returns the full list of heading nodes. """
        return self.root['subs']


# -------------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------------


def esc(text, quotes=True):
    """ Convert html syntax characters to character entities. """
    return html.escape(text, quotes)


def dedent(text, n=None):
    """ Dedent each line by `n` spaces or strip any common leading w'space. """
    if n is None:
        return textwrap.dedent(text)
    else:
        return re.sub(r"^[ ]{%s}" % n, "", text, flags=re.MULTILINE)


def indent(text, n=4):
    """ Indent every non-empty line by `n` spaces. """
    return re.sub(r"^(?=\s*\S.*$)", " " * n, text, flags=re.MULTILINE)


def strip(text):
    """ Strip leading blank lines and all trailing whitespace. """
    text = re.sub(r"^([ ]*\n)*", "", text)
    return text.rstrip()


def strip_tags(text):
    """ Strip all angle-bracket-enclosed substrings. """
    return re.sub(r'<[^>]*>', '', text)


def idify(s):
    """ Process a string for use as an #id. """
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('ascii')
    s = s.lower()
    s = s.replace("'", '')
    s = re.sub(r'[^a-z0-9-]+', '-', s)
    s = re.sub(r'--+', '-', s).strip('-')
    s = re.sub(r'^\d+', '', s)
    return s or 'id'


def error(msg):
    """ Print an error message to stderr. """
    sys.stderr.write('error: ' + msg + '\n')


def title(text, w=80):
    """ Format title text for output on the command line. """
    return '=' * w + '\n' + text.center(w, '-') + '\n' +  '=' * w + '\n'


# -------------------------------------------------------------------------
# Preprocessors
# -------------------------------------------------------------------------


def preprocess(text):
    """ Prepare input text for parsing into a node tree.

    * Convert all line endings to newlines.
    * Convert all tabs to spaces.
    * Escape backslashed characters.
    * Extract footnotes.
    * Extract link references.

    """
    text = re.sub(r"\r\n|\r", r"\n", text)
    text = text.expandtabs(4)
    text = escape_backslashes(text)
    text, footnotes = extract_footnotes(text)
    text, link_refs = extract_link_references(text)
    return text, link_refs, footnotes


def escape_backslashes(text):
    """ Replace backslashed characters with placeholder strings. """

    def callback(match):
        char = match.group(1)
        if char in ESCCHARS:
            return 'esc%s%s%s' % (STX, ord(char), ETX)
        else:
            return match.group(0)

    return re.sub(r"\\(.)", callback, text, flags=re.DOTALL)


def extract_footnotes(text):
    """ Extract footnotes of the form:

        [^ref]: line 1
            line 2
            ...

    The entire footnote block can be indented by any multiple of 4 spaces.

    """
    footnotes = Node('footnotes', {'class': 'stx-footnotes'})
    index = 1
    if not text.endswith('\n'):
        text += '\n'

    def callback(match):
        ref = match.group('ref')
        if not ref:
            nonlocal index
            ref = str(index)
            index += 1
        note_text = match.group('line1').lstrip(' ')
        if match.group('body'):
            indent = len(match.group(1)) + 4
            note_text += dedent(match.group('body'), indent)
        footnote = footnotes.append(Node('footnote'))
        footnote.meta = ref
        footnote.children = BlockParser().parse(note_text)
        return ''

    text = re.sub(
        r"""
        ^(?P<indent>([ ]{4})*)\[\^(?P<ref>[^\]]*)\][:](?P<line1>[^\n]*\n)
        (?P<body>(
            (^(?P=indent)[ ]{4}[ ]*[^ \n]+.*\n)
            |
            (^[ ]*\n)
        )*)
        """,
        callback,
        text,
        flags = re.MULTILINE | re.VERBOSE
    )

    return text, footnotes


def extract_link_references(text):
    """ Extract link references of the form:

        [ref]: http://example.com "optional title"

     """
    refs = {}
    if not text.endswith('\n'):
        text += '\n'

    def callback(match):
        ref = match.group('ref').lower()
        url = match.group('url')
        title = match.group('title') or ''
        refs[ref] = (url, title)
        return ''

    text = re.sub(
        r"""
        ^([ ]{4})*
            \[(?P<ref>[^\]]+)\][:]
                [ ]*(?P<url>\S+)
                    (?:[ ]+"(?P<title>[^"]*)")?
                        [ ]*\n
        """,
        callback,
        text,
        flags = re.MULTILINE | re.VERBOSE
    )
    return text, refs


# -------------------------------------------------------------------------
# Internal Interface
# -------------------------------------------------------------------------


def parse(text):
    text, link_refs, footnotes = preprocess(text)
    root = Node('root')
    root.children = BlockParser().parse(text)
    toc = TOCBuilder(root)
    inserts = {
        'footnotes': footnotes,
        'toc': toc.toc(),
        'fulltoc': toc.fulltoc(),
    }
    return root, link_refs, inserts


def render_html(text):
    root, link_refs, inserts = parse(text)
    rendered = HtmlRenderer(link_refs, inserts).render(root)
    return rendered


def render_debug(text):
    root, link_refs, inserts = parse(text)
    output = []
    output.append('\n\n' + title(' AST '))
    output.append(str(root))
    output.append('\n' + title(' HTML '))
    output.append(HtmlRenderer(link_refs, inserts).render(root))
    return ''.join(output)


# -------------------------------------------------------------------------
# Library Interface
# -------------------------------------------------------------------------


def render(text, debug=False):
    if debug:
        return render_debug(text)
    else:
        return render_html(text)


# -------------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------------


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


class HelpAction(argparse.Action):
    """ Custom argparse action to override the default help text. """
    def __call__(self, parser, namespace, values, option_string=None):
        print(helptext.strip())
        sys.exit()


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-v', '--version',
        action="version",
        version=__version__,
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

    if args.pygmentize:
        global pygmentize
        pygmentize = True

    text = sys.stdin.read()
    rendered = render(text, args.debug)
    sys.stdout.write(rendered + '\n')


if __name__ == '__main__':
    main()
