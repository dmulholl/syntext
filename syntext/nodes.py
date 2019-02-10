# ------------------------------------------------------------------------------
# Node classes for the package's AST.
# ------------------------------------------------------------------------------

import sys
from . import inline


# Input text is parsed into a tree of Node instances.
class Node:

    def __init__(self, tag=None, atts=None):
        self.tag = tag
        self.content = None
        self.children = []
        self.atts = atts or {}

    def __str__(self):
        return self.str()

    def str(self, depth=0):
        output = ["·  " * depth]
        output.append('%s' % self.__class__.__name__)
        if self.tag:
            output.append(' ' + self.opening_tag())
        if self.content:
            text = repr(self.content)
            if len(text) < 40:
                output.append(' ' + text)
            else:
                output.append(' ' + text[:18] + "..." + text[-18:])
        output.append('\n')
        for child in self.children:
            output.append(child.str(depth + 1))
        return ''.join(output)

    def render(self, meta):
        return ''.join(child.render(meta) for child in self.children)

    def text(self):
        return self.content or '\n'.join(child.text() for child in self.children)

    def opening_tag(self):
        attributes = []
        for key, value in sorted(self.atts.items()):
            if value is None:
                attributes.append(' %s' % key)
            else:
                attributes.append(' %s="%s"' % (key, value))
        return '<%s%s>' % (self.tag, ''.join(attributes))

    def closing_tag(self):
        return '</%s>' % self.tag

    def append(self, node):
        self.children.append(node)
        return self

    def add_class(self, newclass):
        classes = self.atts.get('class', '').split()
        if newclass not in classes:
            classes.append(newclass)
            self.atts['class'] = ' '.join(sorted(classes))


# Text nodes contain only text. They have no children.
class Text(Node):

    def __init__(self, text):
        Node.__init__(self)
        self.content = text

    def render(self, meta):
        return inline.render(self.content, meta)


# Base class for nodes with children.
class Block(Node):

    def render(self, meta):
        html = []

        if self.tag:
            html.append(self.opening_tag())
            html.append('\n')

        if isinstance(self, Raw):
            html.append(self.text())
            html.append('\n')
        else:
            html.append(''.join(child.render(meta) for child in self.children))

        if self.tag:
            html.append(self.closing_tag())
            html.append('\n')

        return ''.join(html)


# Leaf nodes cannot contain nested block-level content, e.g. nodes
# representing <p> or <h1> elements.
class Leaf(Block):
    pass


# Container nodes can contain nested block-level content, e.g. nodes
# representing <div> or <ul> elements.
class Container(Block):
    pass


# Raw nodes contain text which should not parsed for inline markup, e.g.
# nodes representing <pre> or <script> elements or raw HTML.
class Raw(Block):
    pass


# Void (or empty) nodes represent elements with no closing tags, e.g. <hr>
# or <img> elements.
class Void(Block):

    def render(self, meta):
        return self.opening_tag() + '\n'


# Comment nodes represent HTML comments.
class Comment(Block):

    def render(self, meta):
        html = []
        html.append('<!--\n')
        html.append(self.text())
        html.append('\n')
        html.append('-->\n')
        return ''.join(html)


# Insert nodes provide a mechanism for inserting generated content,
# e.g. tables of contents or footnotes.
class Insert(Block):

    def render(self, meta):
        if self.content in meta:
            return meta[self.content].render(meta)
        else:
            sys.stderr.write('Error: missing insert %s.\n' % repr(self.content))
            return ''


# Turns on newline-to-linebreak mode for all children.
class Nl2Br(Block):

    def render(self, meta):
        context = meta.setdefault('context', [])
        context.append('nl2br')
        rendered = ''.join(child.render(meta) for child in self.children)
        context.pop()
        return rendered
