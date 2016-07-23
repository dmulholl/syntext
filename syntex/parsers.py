# -------------------------------------------------------------------------
# Parsers for block-level structures.
# -------------------------------------------------------------------------

import re
import html

from . import nodes
from . import utils
from . import tags


# -------------------------------------------------------------------------
# Parsers for individual block-level structures.
# -------------------------------------------------------------------------


# Consumes a H1 heading of the form:
#
#   ======
#    Some
#    Text
#   ======
#
# The upper line of '=' symbols is optional.
class H1Parser:

    def __call__(self, stream, meta):
        lines, found = [], False

        # Loop until we meet a blank line or a line of = symbols.
        while stream.has_next():
            nextline = stream.next()
            lines.append(nextline)
            if nextline:
                if len(lines) > 1 and re.fullmatch(r'=+', nextline):
                    found = True
                    break
            else:
                break

        # If we didn't find a line of = symbols, rewind the stream.
        if found:
            if re.fullmatch(r'=+', lines[0]):
                lines.pop(0)
            text = nodes.Text('\n'.join(lines[:-1]))
            return True, nodes.Leaf('h1').append(text)
        else:
            stream.rewind(len(lines))
            return False, None


# Consumes a H2 heading of the form:
#
#   ------
#    Some
#    Text
#   ------
#
# The upper line of '-' symbols is optional.
class H2Parser:

    def __call__(self, stream, meta):
        lines, found = [], False

        # Loop until we meet a blank line or a line of - symbols.
        while stream.has_next():
            nextline = stream.next()
            lines.append(nextline)
            if nextline:
                if len(lines) > 1 and re.fullmatch(r'-+', nextline):
                    found = True
                    break
            else:
                break

        # If we didn't find a line of - symbols, rewind the stream.
        if found:
            if re.fullmatch(r'-+', lines[0]):
                lines.pop(0)
            text = nodes.Text('\n'.join(lines[:-1]))
            return True, nodes.Leaf('h2').append(text)
        else:
            stream.rewind(len(lines))
            return False, None


# Consumes an arbitrary level heading of the form:
#
#   ### Heading Text ###
#
# The number of leading '#' symbols specifies the heading level. The trailing
# symbols are optional.
class HeadingParser:

    def __call__(self, stream, meta):
        match = re.match(r'([#]{1,6})[ ]+', stream.peek())
        if match:
            line = stream.next()
            text = line.strip('#').strip()
            tag = 'h' + str(len(match.group(1)))
            return True, nodes.Leaf(tag).append(nodes.Text(text))
        else:
            return False, None


# Consumes a sequence of indented lines. The lines must be indented by at
# least 4 spaces. The sequence may include blank lines.
class IndentedCodeParser:

    def __call__(self, stream, meta):
        if stream.peek().startswith('    '):
            lines = utils.LineStream()
            while stream.has_next():
                nextline = stream.peek()
                if nextline == '' or nextline.startswith('    '):
                    lines.append(stream.next())
                else:
                    break
            text = str(lines.dedent().trim())
            text = html.escape(text, False)
            return True, nodes.Raw('pre').append(nodes.Text(text))
        return False, None


# Consumes a line containing three or more '-' or '*' symbols. The symbols
# may optionally be separated by any number of spaces.
class HorizontalRuleParser:

    def __call__(self, stream, meta):
        match = re.match(r'[ ]{0,3}([-*])[ ]*\1[ ]*\1.*', stream.peek())
        if match:
            stream.next()
            return True, nodes.Void('hr')
        else:
            return False, None


# Consumes a single line of text, returning it as a Text node.
class TextParser:

    def __call__(self, stream, meta):
        return True, nodes.Text(stream.next())


# Consumes an unordered list. The list item marker is one of (*, •, -, or +).
# List item markers can be indented by up to three spaces.
#
# Each list item consists of its opening line plus all subsequent blank
# or indented lines. The list item is ended by:
#
#   1. the end of the stream
#   2. a non-indented line
#   3. a line beginning with the same item marker, possibly indented by up
#      three spaces
#
# Example:
#
#     * foo
#     * bar
#     * baz
#
# Switching to a different item marker starts a new list.
class ULParser:

    def __call__(self, stream, meta):
        match = re.fullmatch(r'[ ]{0,3}([*•+-])([ ].+)?', stream.peek())
        if not match:
            return False, None

        # A new marker means a new list.
        marker = match.group(1)
        re_header = r'[ ]{0,3}[%s]([ ].+)?' % marker

        # Read in each individual list item as a new LineStream instance.
        items = []
        while stream.has_next():
            match = re.fullmatch(re_header, stream.peek())
            if match:
                stream.next()
                item = utils.LineStream()
                items.append(item)

                # Read in any indented content.
                while stream.has_next():
                    if re.fullmatch(re_header, stream.peek()):
                        break
                    elif stream.peek().startswith(' ') or stream.peek() == '':
                        item.append(stream.next())
                    else:
                        break

                # We need to dedent the content before prepending the header.
                item.dedent()

                # Prepend the content of the header line.
                if match.group(1):
                    item.prepend(match.group(1).strip())
            else:
                break

        # Determine if we're dealing with a block or compact-style list.
        if len(items) > 1:
            if items[0].has_trailing_blank():
                listtype = 'block'
            else:
                listtype = 'compact'
        else:
            listtype = 'block'

        # Assemble the node tree representing the list.
        ul = nodes.Container('ul')
        for item in items:
            item = item.trim()
            li = nodes.Container('li')
            if listtype == 'block':
                children = ContainerParser().parse(item, meta)
            else:
                parsers = (ULParser(), OLParser(), TextParser())
                children = Parser(parsers).parse(item, meta)
            li.children = children
            ul.append(li)

        return True, ul


# Consumes an ordered list. The list item marker is '#.' or '<int>.'.
# List item markers can be indented by up to three spaces.
#
# Each list item consists of its opening line plus all subsequent blank
# or indented lines. The list item is ended by:
#
#   1. the end of the stream
#   2. a non-indented line
#   3. a line beginning with the same item marker, possibly indented by up
#      three spaces
#
# Example:
#
#     1. foo
#     2. bar
#     3. baz
#
# Switching to a different item marker starts a new list.
class OLParser:

    def __call__(self, stream, meta):
        match = re.fullmatch(r'[ ]{0,3}([#]|\d+)[.]([ ].+)?', stream.peek())
        if not match:
            return False, None

        # A new marker means a new list.
        marker = match.group(1)
        if marker == '#':
            re_header = r'[ ]{0,3}[#][.]([ ].+)?'
        else:
            re_header = r'[ ]{0,3}\d+[.]([ ].+)?'

        # Do we have a custom start value?
        atts = None if marker in ('#', '1') else {'start': marker}

        # Read in each individual list item as a new LineStream instance.
        items = []
        while stream.has_next():
            match = re.fullmatch(re_header, stream.peek())
            if match:
                stream.next()
                item = utils.LineStream()
                items.append(item)

                # Read in any indented content.
                while stream.has_next():
                    if re.fullmatch(re_header, stream.peek()):
                        break
                    elif stream.peek().startswith(' ') or stream.peek() == '':
                        item.append(stream.next())
                    else:
                        break

                # We need to dedent the content before prepending the header.
                item.dedent()

                # Prepend the content of the header line.
                if match.group(1):
                    item.prepend(match.group(1).strip())
            else:
                break

        # Determine if we're dealing with a block or compact-style list.
        if len(items) > 1:
            if items[0].has_trailing_blank():
                listtype = 'block'
            else:
                listtype = 'compact'
        else:
            listtype = 'block'

        # Assemble the node tree representing the list.
        ol = nodes.Container('ol', atts)
        for item in items:
            item = item.trim()
            li = nodes.Container('li')
            if listtype == 'block':
                children = ContainerParser().parse(item, meta)
            else:
                parsers = (ULParser(), OLParser(), TextParser())
                children = Parser(parsers).parse(item, meta)
            li.children = children
            ol.append(li)

        return True, ol


# Consumes a definition list of the form:
#
#   ||  Term 1  ||
#
#       This is the definition of the term.
#
#   ||  Term 2  ||
#
#       This is the definition of the term.
#
class DefinitionListParser:

    def __call__(self, stream, meta):
        match = re.fullmatch(r'\|\|(.+)', stream.peek())
        if not match:
            return False, None

        dl = nodes.Container('dl')
        while stream.has_next():
            match = re.fullmatch(r'\|\|(.+)', stream.peek())
            if match:
                stream.next()

                term = match.group(1).strip('|').strip()
                dt = nodes.Leaf('dt').append(nodes.Text(term))
                dl.append(dt)

                definition = utils.LineStream()
                while stream.has_next():
                    if re.fullmatch(r'\|\|(.+)', stream.peek()):
                        break
                    elif stream.peek().startswith(' ') or stream.peek() == '':
                        definition.append(stream.next())
                    else:
                        break

                dd = nodes.Container('dd')
                dd.children = ContainerParser().parse(definition.dedent(), meta)
                dl.append(dd)
            else:
                break

        return True, dl


# Consumes a sequence of adjacent non-blank lines.
class ParagraphParser:

    def __call__(self, stream, meta):
        lines = []
        while stream.has_next():
            nextline = stream.next()
            if nextline != '':
                lines.append(nextline)
            else:
                break
        return True, nodes.Leaf('p').append(nodes.Text('\n'.join(lines)))


# Consumes one or more lines of raw block-level HTML.
class HtmlParser:

    blocks = [
        'address', 'article', 'aside', 'blockquote', 'body,' 'canvas', 'dd',
        'div', 'dl', 'fieldset', 'figcaption', 'figure', 'footer', 'form',
        'head', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hgroup', 'li',
        'main', 'nav', 'noscript', 'ol', 'output', 'p', 'pre', 'script',
        'section', 'style', 'table', 'tfoot', 'title', 'ul', 'video',
    ]

    def __call__(self, stream, meta):
        match = re.match(r'<([a-zA-Z][^>]*?)>', stream.peek())
        if match and match.group(1) in self.blocks:
            tag = match.group(1)
            lines = [stream.next()]
        else:
            return False, None

        # Do we have a one-liner?
        match = re.fullmatch(r'<([a-zA-Z][^>]*?)>.*</\1>', lines[0])
        if match:
            node = nodes.Raw()
            node.append(nodes.Text(lines[0]))
            return True, node

        # Look for the corresponding closing tag.
        found, endtag = False, '</%s>' % tag
        while stream.has_next():
            lines.append(stream.next())
            if lines[-1] == endtag:
                found = True
                break

        if found:
            node = nodes.Raw()
            node.append(nodes.Text('\n'.join(lines)))
            return True, node
        else:
            sys.stderr.write("Error: missing closing tag '%s'.\n" % endtag)
            return True, None


# Consumes a link reference of the form:
#
#   [ref]: http://example.com optional title text
#
# The content of any following indented lines will be appended to the title.
class LinkRefParser:

    def __call__(self, stream, meta):
        match = re.fullmatch(r'\[([^\]]+)\][:][ ]+(\S+)([ ].+)?', stream.peek())
        if match:
            stream.next()
        else:
            return False, None

        ref = match.group(1).lower()
        url = match.group(2)
        title = match.group(3) or ''

        lines = []
        while stream.has_next():
            if stream.peek().startswith(' ') or stream.peek() == '':
                line = stream.next()
                if line:
                    lines.append(line.strip())
            else:
                break

        if title:
            lines.insert(0, title.strip())
        title = ' '.join(lines)

        meta.setdefault('linkrefs', {})[ref] = (url, title)
        return True, None


# Consumes a tagged block of the form:
#
#   :tag [keyword] [.class1 .class2] [#id] [attr=foo attr="bar"] [@attr]
#       block content
#       block content
#
#       block content
#       ...
#
# The block's content consists of all consecutive blank or indented lines
# following the block header. How this content is processed depends on
# the tag; in the general case content is processed recursively and can
# contain nested block-level structures.
class TaggedBlockParser:

    # Regex for parsing the block's arguments.
    args_regex = re.compile(r"""
        (?:([^\s'"=]+)=)?           # an optional key, followed by...
        (
            "((?:[^\\"]|\\.)*)"     # a double-quoted value, or
            |
            '((?:[^\\']|\\.)*)'     # a single-quoted value
        )
        |
        ([^\s'"=]+)=(\S+)           # a key followed by an unquoted value
        |
        (\S+)                       # an unkeyed, unquoted value
    """, re.VERBOSE)

    def __call__(self, stream, meta):
        match = re.fullmatch(r':([^ ]+)([ ].+)?', stream.peek())
        if match:
            stream.next()
        else:
            return False, None

        tag = match.group(1)
        argstr = match.group(2) or ''
        pargs, kwargs = self.parse_args(argstr)

        content = utils.LineStream()
        while stream.has_next():
            if stream.peek().startswith(' ') or stream.peek() == '':
                content.append(stream.next())
            else:
                break
        content = content.trim().dedent()

        # Hand off responsibility to the registered tag handler.
        return True, tags.process(tag, pargs, kwargs, content, meta)

    def parse_args(self, argstr):
        pargs, kwargs, classes = [], {}, []

        # Parse the argument string into a list of positional and dictionary
        # of keyword arguments.
        for match in self.args_regex.finditer(argstr):
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

        # Parse any .classes, #ids, or @attributes from the list of
        # positional arguments.
        for arg in pargs[:]:
            if arg.startswith('.'):
                classes.append(arg[1:])
                pargs.remove(arg)
            if arg.startswith('#'):
                kwargs['id'] = arg[1:]
                pargs.remove(arg)
            if arg.startswith('&'):
                kwargs[arg.lstrip('&')] = None
                pargs.remove(arg)

        # Convert the classes list into a space-separated string.
        # We need to keep an eye out for a named 'class' attribute.
        if 'class' in kwargs:
            classes.extend(kwargs['class'].split())
        if classes:
            kwargs['class'] = ' '.join(sorted(classes))

        return pargs, kwargs


# -------------------------------------------------------------------------
# Top-level parsers for block structures.
# -------------------------------------------------------------------------


# Base parser class. Parses an input stream into a list of nodes.
class Parser:

    def __init__(self, parsers):
        self.parsers = parsers

    def parse(self, stream, meta):
        nodelist = []
        while stream.has_next():

            # If the next line in the stream is blank, discard it.
            if stream.peek() == '':
                stream.next()
                continue

            # Give each parser an opportunity to parse the stream.
            for parser in self.parsers:
                parsed, result = parser(stream, meta)
                if parsed:
                    if isinstance(result, nodes.Node):
                        nodelist.append(result)
                    break

            # If we have an unparsable line, print an error and skip it.
            if not parsed:
                sys.stderr.write("UNPARSED: %s\n" % stream.next())

        # Merge adjacent text nodes.
        mergedlist = []
        for node in nodelist:
            if mergedlist and isinstance(mergedlist[-1], nodes.Text):
                if isinstance(node, nodes.Text):
                    mergedlist[-1].content += '\n' + node.content
                    continue
            mergedlist.append(node)

        return mergedlist


# Default parser for parsing the content of container elements.
class ContainerParser(Parser):

    # List of structure parsers for parsing the content of container elements,
    # i.e. elements that can contain nested block-level content.
    container_parsers = [
        TaggedBlockParser(),
        IndentedCodeParser(),
        H1Parser(),
        H2Parser(),
        HeadingParser(),
        HorizontalRuleParser(),
        ULParser(),
        OLParser(),
        DefinitionListParser(),
        LinkRefParser(),
        HtmlParser(),
        ParagraphParser(),
    ]

    def __init__(self):
        self.parsers = self.container_parsers


# Default parser for parsing the content of leaf elements.
class LeafParser(Parser):

    # List of structure parsers for parsing the content of leaf elements,
    # i.e. elements that cannot contain nested block-level content.
    leaf_parsers = [
        TaggedBlockParser(),
        TextParser(),
    ]

    def __init__(self):
        self.parsers = self.leaf_parsers
