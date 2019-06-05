# ------------------------------------------------------------------------------
# Parsers for block-level structures.
# ------------------------------------------------------------------------------

import re
import html
import sys

from . import nodes
from . import utils


# ------------------------------------------------------------------------------
# Parsers for individual block-level structures.
# ------------------------------------------------------------------------------


# Consumes an arbitrary-level heading of the form:
#
#   ### Heading Text ###
#
# The number of leading '#' symbols specifies the heading level; trailing
# symbols are optional.
class HeadingParser:

    def __call__(self, stream, meta):
        match = re.match(r'([#]{1,6})[ ]+', stream.peek())
        if match:
            line = stream.next()
            text = nodes.TextNode(line.strip('#').strip())
            tag = 'h' + str(len(match.group(1)))
            return True, nodes.Node(tag).append_child(text)
        else:
            return False, None


# Consumes an outlined, arbitrary-level heading of the form:
#
#   ------------------
#   #  Heading Text  #
#   ------------------
#
class FancyHeadingParser:

    def __call__(self, stream, meta):
        if len(stream.lines) < 3 or not re.fullmatch(r'-+', stream.peek()):
            return False, None

        line1 = stream.next()
        line2 = stream.next()
        line3 = stream.next()

        if re.fullmatch(r'-+', line3):
            match = re.match(r'([#]{1,6})[ ]+', line2)
            if match:
                text = nodes.TextNode(line2.strip('#').strip())
                tag = 'h' + str(len(match.group(1)))
                return True, nodes.Node(tag).append_child(text)

        stream.rewind(3)
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
            text = html.escape(text)
            return True, nodes.Node('pre', text=text)
        return False, None


# Consumes a single line of text, returning it as a Text node.
class TextParser:

    def __call__(self, stream, meta):
        return True, nodes.TextNode(stream.next())


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
class UnorderedListParser:

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
        ul = nodes.Node('ul')
        for item in items:
            item = item.trim()
            li = nodes.Node('li')
            if listtype == 'block':
                children = BlockParser().parse(item, meta)
            else:
                parsers = (UnorderedListParser(), OrderedListParser(), TextParser())
                children = Parser(parsers).parse(item, meta)
            li.children = children
            ul.append_child(li)

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
class OrderedListParser:

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
        ol = nodes.Node('ol', atts)
        for item in items:
            item = item.trim()
            li = nodes.Node('li')
            if listtype == 'block':
                children = BlockParser().parse(item, meta)
            else:
                parsers = (UnorderedListParser(), OrderedListParser(), TextParser())
                children = Parser(parsers).parse(item, meta)
            li.children = children
            ol.append_child(li)

        return True, ol


# Consumes a definition list of the form:
#
#   [[  Term 1  ]]
#
#       This is the definition of the term.
#
#   [[  Term 2  ]]
#
#       This is the definition of the term.
#
class DefinitionListParser:

    def __call__(self, stream, meta):
        match = re.fullmatch(r'\[\[(.+)\]\]', stream.peek())
        if not match:
            return False, None

        dl = nodes.Node('dl')
        while stream.has_next():
            match = re.fullmatch(r'\[\[(.+)\]\]', stream.peek())
            if match:
                stream.next()

                term = match.group(1).lstrip('[').rstrip(']').strip()
                dt = nodes.Node('dt').append_child(nodes.TextNode(term))
                dl.append_child(dt)

                definition = utils.LineStream()
                while stream.has_next():
                    if re.fullmatch(r'\[\[(.+)\]\]', stream.peek()):
                        break
                    elif stream.peek().startswith(' ') or stream.peek() == '':
                        definition.append(stream.next())
                    else:
                        break

                dd = nodes.Node('dd')
                dd.children = BlockParser().parse(definition.dedent(), meta)
                dl.append_child(dd)
            else:
                break

        return True, dl


# Consumes a sequence of adjacent non-blank lines.
class ParagraphParser:

    def __call__(self, stream, meta):
        lines = []
        while stream.has_next():
            if stream.peek() == '':
                break
            lines.append(stream.next())
        text = nodes.TextNode('\n'.join(lines))
        return True, nodes.Node('p').append_child(text)


# Consumes and discards a single blank line.
class BlankLineParser:

    def __call__(self, stream, meta):
        if stream.peek() == '':
            stream.next()
            return True, None
        return False, None


# Consumes one or more lines of raw block-level HTML.
class HtmlParser:

    html_block_tags = """
        address article aside blockquote body canvas dd div dl fieldset 
        figcaption figure footer form head h1 h2 h3 h4 h5 h6 header hgroup
        li main noscript ol output p pre script section style table tfoot
        title ul video html 
    """.split()

    def __call__(self, stream, meta):
        match = re.match(r'<([a-zA-Z][^>]*?)>', stream.peek())
        if match and match.group(1) in self.html_block_tags:
            tag = match.group(1)
            lines = [stream.next()]
        else:
            return False, None

        # Do we have a one-liner?
        match = re.fullmatch(r'<([a-zA-Z][^>]*?)>.*</\1>', lines[0])
        if match:
            return True, nodes.Node(text=lines[0])

        # Look for the corresponding closing tag.
        found, endtag = False, '</%s>' % tag
        while stream.has_next():
            lines.append(stream.next())
            if lines[-1] == endtag:
                found = True
                break

        if found:
            return True, nodes.Node(text='\n'.join(lines))
        else:
            sys.stderr.write("Error: missing closing tag '%s'.\n" % endtag)
            return True, None


# Consumes a link reference.
#
#   [ref]: http://example.com
#     optional title text indented on following line
#
#   [ref]:
#     http://example.com
#     optional title text
#
class LinkRefParser:

    def __call__(self, stream, meta):
        match = re.match(r'\[([^\]]+)\][:][ ]*(\S+)?', stream.peek())
        if match:
            stream.next()
        else:
            return False, None

        ref = match.group(1).lower()
        url = match.group(2) or ''

        lines = []
        while stream.has_next():
            if stream.peek().startswith(' ') or stream.peek() == '':
                line = stream.next()
                if line:
                    lines.append(line.strip())
            else:
                break

        if lines and not url:
            url = lines[0]
            lines.pop(0)

        title = ' '.join(lines).strip()

        meta.setdefault('linkrefs', {})[ref] = (url, title)
        return True, None


# Consumes a shorthand html block of the form:
#
#   :tag [keyword] [.class] [#id] [attr=foo attr="bar"] [&attr]
#       block content
#       ...
#
# The block's content consists of all consecutive blank or indented lines
# following the block header. How this content is processed depends on
# the tag; in the general case content is processed recursively and can
# contain nested block-level structures.
class ShorthandParser:

    argparser = utils.ArgParser()

    def __call__(self, stream, meta):
        match = re.fullmatch(r':([^ ]+)([ ].+)?', stream.peek())
        if match:
            stream.next()
        else:
            return False, None

        tag = match.group(1)
        argstring = match.group(2) or ''
        pargs, kwargs = self.argparser.parse(argstring)

        content = utils.LineStream()
        while stream.has_next():
            if stream.peek().startswith(' ') or stream.peek() == '':
                content.append(stream.next())
            else:
                break
        content = content.trim().dedent()

        from . import shorthand
        return True, shorthand.process(tag, pargs, kwargs, content, meta)



class TagParser:

    argparser = utils.ArgParser()

    def __call__(self, stream, meta):
        if not stream.peek().startswith('::: '):
            return False, None

        header = stream.next()
        if header.endswith(' :::'):
            is_empty = True
        else:
            is_empty = False
            
        header = header.strip(':')
        elements = header.split(maxsplit=1)
        if len(elements) == 2:
            tag, argstring = elements[0], elements[1]
        elif len(elements) == 1:
            tag, argstring = elements[0], ''
        else:
            tag, argstring = '', ''
        pargs, kwargs = self.argparser.parse(argstring)

        content = utils.LineStream()
        if is_empty:
            from . import tags
            return True, tags.process(tag, pargs, kwargs, content, meta)

        open_tags = 1
        found_end = False
        while stream.has_next():
            next = stream.peek().strip()
            if next == '::: end':
                if open_tags == 1:
                    found_end = True
                    stream.next()
                    break
                else:
                    open_tags -= 1
            elif next.startswith('::: ') and not next.endswith(' :::'):
                open_tags += 1
            content.append(stream.next())
        content = content.trim().dedent()

        if found_end:
            from . import tags
            return True, tags.process(tag, pargs, kwargs, content, meta)
        else:
            sys.stderr.write("Error: missing end tag for '%s' block.\n" % tag)
            return True, None
            

# ------------------------------------------------------------------------------
# Top-level parsers for block structures.
# ------------------------------------------------------------------------------


# Base parser class. Parses an input stream into a list of nodes.
class Parser:

    def __init__(self, parsers):
        self.parsers = parsers

    def parse(self, stream, meta):
        nodelist = []
        while stream.has_next():

            # Give each parser an opportunity to parse the stream.
            for parser in self.parsers:
                match, result = parser(stream, meta)
                if match:
                    if isinstance(result, nodes.Node):
                        nodelist.append(result)
                    break

            # If we have an unparsable line, print an error and skip it.
            if not match:
                sys.stderr.write("UNPARSEABLE: %s\n" % stream.next())

        # Merge adjacent text nodes.
        mergedlist = []
        for node in nodelist:
            if mergedlist and isinstance(mergedlist[-1], nodes.TextNode):
                if isinstance(node, nodes.TextNode):
                    mergedlist[-1].text += '\n' + node.text
                    continue
            mergedlist.append(node)

        return mergedlist


# Default parser for parsing the content of block-level elements.
class BlockParser(Parser):

    parser_list = [
        BlankLineParser(),
        TagParser(),
        ShorthandParser(),
        IndentedCodeParser(),
        HeadingParser(),
        FancyHeadingParser(),
        UnorderedListParser(),
        OrderedListParser(),
        DefinitionListParser(),
        LinkRefParser(),
        HtmlParser(),
        ParagraphParser(),
    ]

    def __init__(self):
        self.parsers = self.parser_list


# Default parser for parsing the content of leaf and inline elements.
class InlineParser(Parser):

    parser_list = [
        TagParser(),
        ShorthandParser(),
        TextParser(),
    ]

    def __init__(self):
        self.parsers = self.parser_list


# Default parser for parsing the content of compact list items.
class ListItemParser(Parser):

    parser_list = [
        UnorderedListParser(), 
        OrderedListParser(), 
        TextParser()
    ]

    def __init__(self):
        self.parsers = self.parser_list