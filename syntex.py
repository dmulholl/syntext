#!/usr/bin/env python3
"""
Syntex
======

A lightweight markup language for generating HTML.

To use as a script:

    $ syntex.py < input.txt > output.html

To use as a library module:

    import syntex
    html, meta = syntex.render(text)

License: This work has been placed in the public domain.

"""

__version__ = "0.9.0"


import sys
import re
import collections
import hashlib
import unicodedata
import argparse
import pprint
import textwrap
import html


# Parse document metadata with the PyYAML module, if available.
try:
    import yaml
except ImportError:
    yaml = None


# Use the Pygments module for syntax highlighting, if available.
try:
    import pygments
    import pygments.lexers
    import pygments.formatters
except ImportError:
    pygments = None


# The following characters can be escaped with a backslash.
ESCCHARS = '\\*:`[]#=-!().•'


# Placeholders to substitute for escaped characters during preprocessing.
STX = '\x02'
ETX = '\x03'
ESCBS = 'esc%s%s%s' % (STX, ord('\\'), ETX)
ESCMAP = {'esc%s%s%s' % (STX, ord(c), ETX): c for c in ESCCHARS}


# Maps block :tagnames to their associated handler functions.
tagmap = {}


# ----------------------------------------------------------------------------
# Block Parser
# ----------------------------------------------------------------------------


class Element:

    """ Input text is parsed into a tree of Element nodes. """

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

    def append(self, element):
        self.children.append(element)
        return element

    def add_class(self, newclass):
        classes = self.attrs.get('class', '').split()
        if not newclass in classes:
            classes.append(newclass)
            self.attrs['class'] = ' '.join(sorted(classes))


class Text(Element):

    """ Shortcut subclass for creating tag="text" nodes. """

    def __init__(self, text):
        Element.__init__(self, 'text')
        self.text = text


class ParagraphProcessor:

    """ A sequence of non-empty lines. """

    regex = re.compile(r"(^[ ]*[^ \n]+.*\n)+", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        element = Element('p')
        element.append(Text(strip(match.group(0))))
        return True, element, match.end(0)


class CodeProcessor:

    """ A sequence of indented or empty lines. """

    regex = re.compile(r"""
        ^[ ]{4}[^ \n]+.*\n
        ((
            (^[ ]*\n)
            |
            (^[ ]{4}.+\n)
        )*)
        """, re.VERBOSE | re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        element = Element('pre')
        element.append(Text(dedent(strip(match.group(0)))))
        return True, element, match.end(0)


class H1Processor:

    """ H1 heading of the form:

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
        element = Element('h1')
        element.append(Text(match.group(1).strip()))
        return True, element, match.end(0)


class H2Processor:

    """ H2 heading of the form:

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
        element = Element('h2')
        element.append(Text(match.group(1).strip()))
        return True, element, match.end(0)


class HeadingProcessor:

    """ Arbitrary level heading of the form:

        === Heading ===
    or
        ### Heading ###

    The number of leading '=' specifies the heading level.
    Trailing '=' are optional.

    """

    regex = re.compile(r"^([=#]{1,6})(.+?)[=#]*\n", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        tag = 'h' + str(len(match.group(1)))
        element = Element(tag)
        element.append(Text(match.group(2).strip()))
        return True, element, match.end(0)


class EmptyLineProcessor:

    """ Skips empty lines. """

    regex = re.compile(r"(^[ ]*\n)+", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        return True, None, match.end(0)


class SkipLineProcessor:

    """ Skips a single line of text. """

    regex = re.compile(r"^.*\n", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        return True, None, match.end(0)


class TextProcessor:

    """ A single non-empty line of text. """

    regex = re.compile(r"^[ ]*[^ \n]+.*\n", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        return True, Text(match.group(0)), match.end(0)


class HorizontalRuleProcessor:

    """ A line containing three or more '-' or '*' characters.

    The characters may optionally be separated by spaces.

    """

    regex = re.compile(r"^[ ]{0,3}([-*])[ ]*\1[ ]*\1.*\n", re.MULTILINE)

    def __call__(self, text, pos):
        match = self.regex.match(text, pos)
        if not match:
            return False, None, pos
        return True, Element('hr'), match.end(0)


class UnorderedListProcessor:

    """ An unordered list. The list item marker is '*' or '•'.

    Each list item consists of its opening line plus all subsequent blank
    or indented lines. List item markers can be indented by up to three spaces.

    """

    item = r"""
        ^[ ]{0,3}[*•](\n|(?:[ ].*\n))
        ((
            (^[ ]*\n)
            |
            (^[ ]+.+\n)
        )*)
    """

    re_item = re.compile(item, re.VERBOSE | re.MULTILINE)
    re_list = re.compile(r"(%s)+" % item, re.VERBOSE | re.MULTILINE)
    re_empt = re.compile(r"^[ ]*\n", re.MULTILINE)

    def __call__(self, text, pos):
        list_match = self.re_list.match(text, pos)
        if not list_match:
            return False, None, pos
        if self.re_empt.search(list_match.group(0).strip()):
            meta = 'block'
            processors = ()
        else:
            meta = 'compact'
            processors = ('empty', 'ul', 'ol', 'text')
        ul = Element('ul', meta=meta)
        for item_match in self.re_item.finditer(list_match.group(0)):
            head = item_match.group(1).lstrip(' ')
            body = item_match.group(2)
            content = head + dedent(body)
            li = ul.append(Element('li', meta=meta))
            li.children = BlockParser(*processors).parse(content)
        return True, ul, list_match.end(0)


class OrderedListProcessor:

    """ An ordered list. The list item marker is '#.' or '<int>.'.

    Each list item consists of its opening line plus all subsequent blank
    or indented lines. List item markers can be indented by up to three spaces.

    """

    item = r"""
        ^[ ]{0,3}(\#|\d+)\.(\n|(?:[ ].*\n))
        ((
            (^[ ]*\n)
            |
            (^[ ]+.+\n)
        )*)
    """

    re_item = re.compile(item, re.VERBOSE | re.MULTILINE)
    re_list = re.compile(r"(%s)+" % item, re.VERBOSE | re.MULTILINE)
    re_empt = re.compile(r"^[ ]*\n", re.MULTILINE)

    def __call__(self, text, pos):
        first_item_match = self.re_item.match(text, pos)
        if not first_item_match:
            return False, None, pos
        list_match = self.re_list.match(text, pos)
        if self.re_empt.search(list_match.group(0).strip()):
            meta = 'block'
            processors = ()
        else:
            meta = 'compact'
            processors = ('empty', 'ul', 'ol', 'text')
        if first_item_match.group(1) in ('#', '1'):
            ol = Element('ol', meta=meta)
        else:
            ol = Element('ol', {'start': first_item_match.group(1)}, meta=meta)
        for item_match in self.re_item.finditer(list_match.group(0)):
            head = item_match.group(2).lstrip(' ')
            body = item_match.group(3)
            content = head + dedent(body)
            li = ol.append(Element('li', meta=meta))
            li.children = BlockParser(*processors).parse(content)
        return True, ol, list_match.end(0)


class DefinitionListProcessor:

    """ A definition list of the form:

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
        dl = Element('dl')
        for item_match in self.re_item.finditer(list_match.group(0)):
            dt = dl.append(Element('dt'))
            dt.append(Text(item_match.group(1).strip()))
            dd = dl.append(Element('dd'))
            dd.children = BlockParser().parse(dedent(item_match.group(2)))
        return True, dl, list_match.end(0)


class GenericBlockProcessor:

    """ A generic block of the form:

        :tag [keyword] [.class1 .class2] [#id] [attr1=foo attr2="bar"]
            block content
            block content

            block content
            ...

    The block's content consists of all consecutive blank or indented lines
    following the block header. How this content is processed depends on
    the tag; in the general case content is processed recursively and can
    contain any block-level structures.

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
            element = tagmap[tag](tag, pargs, kwargs, content)
        else:
            element = None

        return True, element, match.end(0)

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
                match, element, pos = processor(text, pos)
                if match:
                    if element:
                        if element.tag == 'text' and elements and \
                            elements[-1].tag == 'text':
                            elements[-1].text += element.text
                        else:
                            elements.append(element)
                    break
        return elements


# ----------------------------------------------------------------------------
# Tag Handlers
# ----------------------------------------------------------------------------


def register(*tags):

    """ Decorator function for registering tag handlers. """

    def register_tag_handler(func):
        for tag in tags:
            tagmap[tag] = func

    return register_tag_handler


@register('div')
def div_handler(tag, pargs, kwargs, content):
    element = Element('div', kwargs)
    element.children = BlockParser().parse(content)
    return element


@register('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
def heading_handler(tag, pargs, kwargs, content):
    element = Element(tag, kwargs)
    element.append(Text(strip(content)))
    return element


@register('blockquote', 'quote', '>>')
def blockquote_handler(tag, pargs, kwargs, content):
    element = Element('blockquote', kwargs)
    element.children = BlockParser().parse(content)
    return element


@register('code', 'pre', '::')
def code_handler(tag, pargs, kwargs, content):
    element = Element('pre', kwargs)
    element.append(Text(strip(content)))
    if pargs:
        element.meta = pargs[0]
        element.attrs['data-lang'] = pargs[0]
        element.add_class('lang-' + pargs[0])
    return element


@register('nl2br', '||')
def nl2lb_handler(tag, pargs, kwargs, content):
    element = Element('nl2br')
    element.children = BlockParser().parse(content)
    return element


@register('alert', '!!')
def alertbox_handler(tag, pargs, kwargs, content):
    element = Element('div', kwargs)
    element.add_class('stx-alert')
    if pargs:
        for arg in pargs:
            element.add_class('stx-%s' % arg)
    element.children = BlockParser().parse(content)
    return element


@register('table', '++')
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
            align[i] = 'stx-align-center'
        elif cell.startswith(':'):
            align[i] = 'stx-align-left'
        elif cell.endswith(':'):
            align[i] = 'stx-align-right'

    def make_row(cells, celltag):
        tr = Element('tr')
        for i, cell in enumerate(cells):
            el = tr.append(Element(celltag))
            if align[i]:
                el.add_class(align[i])
            el.append(Text(cell))
        return tr

    table = Element('table', kwargs)
    thead = table.append(Element('thead'))
    tbody = table.append(Element('tbody'))
    thead.append(make_row(head, 'th'))
    for row in body:
        tbody.append(make_row(row, 'td'))
    return table


@register('raw', ESCBS)
def raw_handler(tag, pargs, kwargs, content):
    element = Element('raw', kwargs)
    element.append(Text(strip(content)))
    return element


@register('image', 'img')
def image_handler(tag, pargs, kwargs, content):
    element = Element('image', kwargs)
    if not 'src' in kwargs:
        element.attrs['src'] = pargs[0] if pargs else ''
    if not 'alt' in kwargs:
        element.attrs['alt'] = esc(strip(content)).replace('\n', ' ')
    return element


@register('null', '<<')
def null_handler(tag, pargs, kwargs, content):
    element = Element('null')
    element.children = BlockParser().parse(content)
    classes = kwargs.get('class', '').split()
    for child in element:
        attrs = kwargs.copy()
        attrs.update(child.attrs)
        child.attrs = attrs
        for cssclass in classes:
            child.add_class(cssclass)
    return element


@register('insert')
def insert_handler(tag, pargs, kwargs, content):
    element = Element('insert', kwargs)
    element.meta = pargs[0] if pargs else ''
    return element


@register('ignore', '//')
def ignore_handler(tag, pargs, kwargs, content):
    return None


@register('comment')
def html_comment_handler(tag, pargs, kwargs, content):
    element = Element('comment')
    element.append(Text(strip(content)))
    return element


# ----------------------------------------------------------------------------
# Renderers
# ----------------------------------------------------------------------------


class BaseHtmlRenderer:

    """ Common base class for both the HTML and Markdown renderers.

    The constructor accepts optional dictionaries of link references and
    insertable elements to use while rendering the element tree.

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

    def render(self, element):
        rendered = self._render(element)
        for key, value in self.hashes.items():
            rendered = rendered.replace(key, value)
        for key, value in ESCMAP.items():
            rendered = rendered.replace(key, value)
        if self.link_refs:
            rendered += self._render_link_refs()
        return strip(rendered)

    def _render(self, element):
        # Subclasses override this method to handle block-level elements.
        return ''

    def _hash(self, text):
        digest = hashlib.sha1(text.encode()).hexdigest()
        self.hashes[digest] = text
        return digest

    def _do_inline_html(self, text):
        return self.re_html.sub(lambda m: self._hash(m.group()), text)

    def _do_inline_entities(self, text):
        return self.re_entity.sub(lambda m: self._hash(m.group()), text)

    def _do_inline_backticks(self, text):
        return self.re_backticks.sub(self._backticks_callback, text)

    def _backticks_callback(self, match):
        return self._hash('<code>%s</code>' % esc(match.group(1), False))

    def _do_inline_strong(self, text):
        return self.re_strong.sub(r"<strong>\1</strong>", text)

    def _do_inline_emphasis(self, text):
        return self.re_emphasis.sub(r"<em>\1</em>", text)

    def _do_inline_bracketed_urls(self, text):
        return self.re_bracketed_url.sub(r'<a href="\1">\1</a>', text)

    def _do_inline_bare_urls(self, text):
        return self.re_bare_url.sub(r'\1<a href="\2\3">\2\3</a>\4', text)

    def _do_inline_images(self, text):
        return self.re_img.sub(self._image_callback, text)

    def _image_callback(self, match):
        alt = esc(match.group(1))
        url = match.group(2)
        title = esc(match.group(3) or '')
        if title:
            return r'<img src="%s" alt="%s" title="%s"/>' % (url, alt, title)
        else:
            return r'<img src="%s" alt="%s"/>' % (url, alt)

    def _do_inline_ref_images(self, text):
        return self.re_ref_img.sub(self._ref_image_callback, text)

    def _ref_image_callback(self, match):
        alt = match.group(1)
        ref = match.group(2).lower() if match.group(2) else alt.lower()
        url, title = self.link_refs.get(ref, ('', ''))
        if title:
            return '<img src="%s" alt="%s" title="%s"/>' % (
                url, esc(alt), esc(title)
            )
        else:
            return '<img src="%s" alt="%s"/>' % (url, esc(alt))

    def _do_inline_links(self, text):
        return self.re_link.sub(self._link_callback, text)

    def _link_callback(self, match):
        text = match.group(1)
        url = match.group(2)
        title = esc(match.group(3) or '')
        if title:
            return r'<a href="%s" title="%s">%s</a>' % (url, title, text)
        else:
            return r'<a href="%s">%s</a>' % (url, text)

    def _do_inline_ref_links(self, text):
        return self.re_ref_link.sub(self._ref_link_callback, text)

    def _ref_link_callback(self, match):
        text = match.group(1)
        ref = match.group(2).lower() if match.group(2) else text.lower()
        url, title = self.link_refs.get(ref, ('#', ''))
        if title:
            return '<a href="%s" title="%s">%s</a>' % (url, esc(title), text)
        else:
            return '<a href="%s">%s</a>' % (url, text)

    def _do_inline_footnotes(self, text):
        return self.re_footnote.sub(self._footnote_callback, text)

    def _footnote_callback(self, match):
        if match.group(1):
            ref = match.group(1)
        else:
            ref = self.footnote_index
            self.footnote_index += 1
        return '<sup class="fn-ref"><a href="#fn-%s">%s</a></sup>' % (ref, ref)


class HtmlRenderer(BaseHtmlRenderer):

    """ Renders an Element tree as HTML.

        html = HtmlRenderer(link_refs, inserts).render(element)

    """

    def _render(self, element):
        method = '_render_%s' % element.tag
        if hasattr(self, method):
            return getattr(self, method)(element)
        else:
            return self._render_default(element)

    def _render_default(self, element):
        if element.tag in (
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'th', 'td', 'dt'
        ):
            html = [element.get_tag()]
        else:
            html = [element.get_tag(), '\n']
        for child in element:
            html.append(self._render(child))
        html.append('</%s>\n' % element.tag)
        return ''.join(html)

    def _render_root(self, element):
        return ''.join(self._render(child) for child in element)

    def _render_null(self, element):
        return ''.join(self._render(child) for child in element)

    def _render_pre(self, element):
        text = element.get_text()
        if pygments and element.meta:
            try:
                lexer = pygments.lexers.get_lexer_by_name(element.meta)
            except pygments.util.ClassNotFound:
                try:
                    lexer = pygments.lexers.guess_lexer(text)
                except pygments.util.ClassNotFound:
                    lexer = None
            if lexer:
                element.add_class('stx-pygments')
                formatter = pygments.formatters.HtmlFormatter(nowrap=True)
                text = strip(pygments.highlight(text, lexer, formatter))
            else:
                text = esc(text, False)
        else:
            text = esc(text, False)
        return ''.join([element.get_tag(), '\n', text, '\n</pre>\n'])

    def _render_image(self, element):
        return element.get_tag('img', close=True) + '\n'

    def _render_hr(self, element):
        return element.get_tag() + '\n'

    def _render_insert(self, element):
        if element.meta in self.inserts:
            insert = self.inserts[element.meta]
            insert.attrs.update(element.attrs)
            return self._render(insert)
        else:
            return ''

    def _render_footnotes(self, element):
        html = [element.get_tag('dl'), '\n']
        for fnote in element:
            html.append('<dt id="fn-%s">%s</dt>\n' % (fnote.meta, fnote.meta))
            html.append('<dd>\n')
            for child in fnote:
                html.append(self._render(child))
            html.append('</dd>\n')
        html.append('</dl>\n')
        return ''.join(html)

    def _render_raw(self, element):
        return element.get_text() + '\n'

    def _render_comment(self, element):
        html = ['<!--\n']
        html.append(indent(element.get_text()))
        html.append('\n-->\n')
        return ''.join(html)

    def _render_nl2br(self, element):
        self.context.append('nl2br')
        html = ''.join(self._render(child) for child in element)
        self.context.pop()
        return html

    def _render_text(self, element):
        text = element.text
        text = self._do_inline_backticks(text)
        text = self._do_inline_bracketed_urls(text)
        text = self._do_inline_html(text)
        text = self._do_inline_entities(text)
        text = esc(text, False)
        text = self._do_inline_strong(text)
        text = self._do_inline_emphasis(text)
        text = self._do_inline_images(text)
        text = self._do_inline_ref_images(text)
        text = self._do_inline_links(text)
        text = self._do_inline_ref_links(text)
        text = self._do_inline_footnotes(text)
        # text = self._do_inline_bare_urls(text)
        text = text.rstrip('\n')
        if 'nl2br' in self.context:
            text = text.replace('\n', '<br>\n')
        return text

    def _render_link_refs(self):
        return ''


class MarkdownRenderer(BaseHtmlRenderer):

    """ Makes a best-effort attempt at rendering an Element tree as Markdown.

        markdown = MarkdownRenderer(link_refs, inserts).render(element)

    Footnotes and footnote references are rendered in HTML.

    The table of contents cannot be rendered as we have no way of setting IDs
    on the document's headings.

    Complex block-level markup is rendered in html unless it occurs
    inside an indented block (i.e. inside a list), as markdown does not
    support indented block-level html.

    """

    def _render(self, element, depth=0):
        method = '_render_%s' % element.tag
        if hasattr(self, method):
            return getattr(self, method)(element, depth)
        elif element.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            return self._render_heading(element, depth)
        else:
            return self._render_default(element, depth)

    def _render_default(self, element, depth):
        if depth == 0:
            return HtmlRenderer().render(element) + '\n\n'
        else:
            error("cannot render indented '%s' block in markdown" % element.tag)
            return ''

    def _render_root(self, element, depth):
        return ''.join(self._render(child, depth) for child in element)

    def _render_null(self, element, depth):
        return ''.join(self._render(child, depth) for child in element)

    def _render_nl2br(self, element, depth):
        self.context.append('nl2br')
        md = ''.join(self._render(child, depth) for child in element)
        self.context.pop()
        return md

    def _render_p(self, element, depth):
        return ''.join(self._render(child, depth) for child in element) + '\n\n'

    def _render_blockquote(self, element, depth):
        md = ''.join(self._render(child) for child in element)
        md = re.sub(r"^", "> ", strip(md), flags=re.MULTILINE)
        return indent(md, depth * 4) + '\n\n'

    def _render_heading(self, element, depth):
        text = element.get_text().replace('\n', ' ')
        text = '#' * int(element.tag[1]) + ' '  + text
        text = indent(text, depth * 4)
        return text + '\n\n'

    def _render_pre(self, element, depth):
        return indent(element.get_text(), (depth + 1) * 4) + '\n\n'

    def _render_hr(self, element, depth):
        return '* * *\n\n'

    def _render_image(self, element, depth):
        md = '![%(alt)s](%(src)s)\n\n' % element.attrs
        return indent(md, depth * 4)

    def _render_raw(self, element, depth):
        if depth == 0:
            return element.get_text() + '\n\n'
        else:
            error("cannot render indented 'raw' block in markdown")
            return ''

    def _render_ul(self, element, depth):
        md = []
        for li in element:
            rendered = self._render(li, 1)
            rendered = ' *  ' + rendered[4:]
            rendered = indent(rendered, depth * 4)
            md.append(rendered)
        if element.meta == 'compact':
            if self.context[-1] != 'compact':
                md.append('\n')
        return ''.join(md)

    def _render_ol(self, element, depth):
        md = []
        for i, li in enumerate(element):
            rendered = self._render(li, 1)
            rendered = ' %s. ' % (i + 1) + rendered[4:]
            rendered = indent(rendered, depth * 4)
            md.append(rendered)
        if element.meta == 'compact':
            if self.context[-1] != 'compact':
                md.append('\n')
        return ''.join(md)

    def _render_li(self, element, depth):
        if element.meta == 'compact':
            self.context.append('compact')
        md = []
        for child in element:
            item = self._render(child, depth)
            if not item.endswith('\n'):
                item += '\n'
            md.append(item)
        if element.meta == 'compact':
            self.context.pop()
        return ''.join(md)

    def _render_insert(self, element, depth):
        if element.meta in ('toc', 'fulltoc'):
            error("cannot render table of contents in markdown")
            return ''
        elif element.meta in self.inserts:
            insert = self.inserts[element.meta]
            insert.attrs.update(element.attrs)
            return self._render(insert, depth)
        else:
            return ''

    def _render_text(self, element, depth):
        text = element.text
        text = self._do_inline_footnotes(text)
        text = text.rstrip('\n')
        if 'nl2br' in self.context:
            text = text.replace('\n', '  \n')
        return indent(text, depth * 4)

    def _render_link_refs(self):
        refs = []
        for ref, data in self.link_refs.items():
            if data[1]:
                refs.append('[%s]: %s "%s"' % (ref, data[0], data[1]))
            else:
                refs.append('[%s]: %s' % (ref, data[0]))
        return '\n'.join(refs)


# ----------------------------------------------------------------------------
# Table of Contents Builder
# ----------------------------------------------------------------------------


class TOCBuilder:

    """ Table of Contents Builder

    Processes a tree of block elements to produce a table of contents
    with links to each heading in the document. Note that this process
    modifies the tree in place by adding an automatically generated ID
    to any heading element that lacks one.

    The table is returned as an Element tree representing an unordered
    list with nested sublists.

        toc = TOCBuilder(doctree).toc()

    """

    def __init__(self, tree):
        self.renderer = HtmlRenderer()
        self.root = dict(level=0, text='ROOT', id='', subs=[])
        self.stack = [self.root]
        self.ids = []
        self._process_element(tree)

    def _process_element(self, element):
        if element.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            node = self._make_heading_node(element)
            while node['level'] <= self.stack[-1]['level']:
                self.stack.pop()
            self.stack[-1]['subs'].append(node)
            self.stack.append(node)
        else:
            for child in element:
                self._process_element(child)

    def _make_heading_node(self, element):
        level = int(element.tag[1])
        html = self.renderer.render(element)
        text = strip_tags(html)
        if 'id' in element.attrs:
            id = element.attrs['id']
        else:
            index = 2
            slug = idify(text)
            id = slug
            while id in self.ids:
                id = '%s-%s' % (slug, index)
                index += 1
            element.attrs['id'] = id
        self.ids.append(id)
        return dict(level=level, text=text, id=id, subs=[])

    def toc(self):
        """ Skips over root-level H1 headings. """
        ul = Element('ul', {'class': 'stx-toc'}, meta='compact')
        for node in self.root['subs']:
            if node['level'] == 1:
                for subnode in node['subs']:
                    ul.append(self._make_li_element(subnode))
            else:
                ul.append(self._make_li_element(node))
        return ul

    def fulltoc(self):
        """ Includes root-level H1 headings. """
        ul = Element('ul', {'class': 'stx-toc'}, meta='compact')
        for node in self.root['subs']:
            ul.append(self._make_li_element(node))
        return ul

    def _make_li_element(self, node):
        li = Element('li', meta='compact')
        li.append(Text('[%s](#%s)' % (node['text'], node['id'])))
        if node['subs']:
            ul = li.append(Element('ul', meta='compact'))
            for child in node['subs']:
                ul.append(self._make_li_element(child))
        return li

    def nodes(self):
        """ Returns the full list of heading nodes. """
        return self.root['subs']


# ----------------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------------


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


# ----------------------------------------------------------------------------
# Preprocessors
# ----------------------------------------------------------------------------


def preprocess(text):
    """ Prepare input text for parsing into an element tree.

    * Convert all line endings to newlines.
    * Convert all tabs to spaces.
    * Extract document meta data.
    * Escape backslashed characters.
    * Extract footnotes.
    * Extract link references.

    """
    text = re.sub(r"\r\n|\r", r"\n", text)
    text = text.expandtabs(4)
    text, meta = extract_meta(text)
    text = escape_backslashes(text)
    text, footnotes = extract_footnotes(text)
    text, link_refs = extract_link_references(text)
    return text, meta, link_refs, footnotes


def extract_meta(text):
    """ Extract document meta and parse it as yaml. """
    meta = {}
    match = re.match(r"^---\n(.*?\n)[-.]{3}\n", text, re.DOTALL)
    if match:
        text = text[match.end(0):]
        if yaml:
            meta = yaml.load(match.group(1))
            meta = meta if isinstance(meta, dict) else {}
    return text, meta


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
    footnotes = Element('footnotes', {'class': 'stx-footnotes'})
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
        footnote = footnotes.append(Element('footnote'))
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


# ----------------------------------------------------------------------------
# Private Interface
# ----------------------------------------------------------------------------


def parse(text):
    text, meta, link_refs, footnotes = preprocess(text)
    root = Element('root')
    root.children = BlockParser().parse(text)
    toc = TOCBuilder(root)
    inserts = {
        'footnotes': footnotes,
        'toc': toc.toc(),
        'fulltoc': toc.fulltoc(),
    }
    meta['[toc]'] = toc.nodes()
    return root, meta, link_refs, inserts


def render_html(text):
    root, meta, link_refs, inserts = parse(text)
    rendered = HtmlRenderer(link_refs, inserts).render(root)
    return rendered, meta


def render_markdown(text):
    root, meta, link_refs, inserts = parse(text)
    rendered = MarkdownRenderer(link_refs, inserts).render(root)
    return rendered, meta


def render_debug(text):

    def heading(title, w=80):
        return '=' * w + '\n' + title.center(w, '-') + '\n' +  '=' * w + '\n'

    root, meta, link_refs, inserts = parse(text)
    output = [heading(' Meta ')]
    output.append(pprint.pformat(meta))
    output.append('\n\n' + heading(' Tree '))
    output.append(str(root))
    output.append('\n' + heading(' HTML '))
    output.append(HtmlRenderer(link_refs, inserts).render(root))
    output.append('\n\n' + heading(' Markdown '))
    output.append(MarkdownRenderer(link_refs, inserts).render(root))
    return ''.join(output), meta


# ----------------------------------------------------------------------------
# Public Interface
# ----------------------------------------------------------------------------


def render(text, format='html'):
    if format in ('markdown', 'm'):
        rendered, meta = render_markdown(text)
    elif format in ('debug', 'd'):
        rendered, meta = render_debug(text)
    else:
        rendered, meta = render_html(text)
    return rendered, meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-V', '--version',
        action="version",
        version=__version__,
    )
    parser.add_argument('-f',
        help="output format: html, markdown, or debug (default: html)",
        default='html',
        dest='format',
    )
    args = parser.parse_args()
    text = sys.stdin.read()
    rendered, meta = render(text, args.format)
    sys.stdout.write(rendered + '\n')


if __name__ == '__main__':
    main()
