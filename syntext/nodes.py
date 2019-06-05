# ------------------------------------------------------------------------------
# Node classes for the package's AST.
# ------------------------------------------------------------------------------

import sys
from . import inline


# Input text is parsed into a tree of nodes.
class Node:

    def __init__(self, tag=None, attributes=None, text=None, is_void=False):
        self.tag = tag
        self.text = text or ''
        self.children = []
        self.attributes = attributes or {}
        self.is_void = is_void

    def __str__(self):
        return self.str()

    def str(self, depth=0):
        output = ["·  " * depth]
        output.append('%s' % self.__class__.__name__)
        if self.tag:
            output.append(' ' + self.opening_tag())
        if self.text:
            text = repr(self.text)
            if len(text) < 40:
                output.append(' ' + text)
            else:
                output.append(' ' + text[:18] + "..." + text[-18:])
        output.append('\n')
        for child in self.children:
            output.append(child.str(depth + 1))
        return ''.join(output)

    def render(self, meta):
        output = []
        if self.tag:
            output.append(self.opening_tag() + '\n')
        if self.children:
            output.append(''.join(child.render(meta) for child in self.children))
        elif self.text:
            output.append(self.text.rstrip() + '\n')
        if self.tag and not self.is_void:
            output.append(self.closing_tag() + '\n')
        return ''.join(output)
            
    def opening_tag(self):
        attributes = []
        for key, value in sorted(self.attributes.items()):
            if value is None:
                attributes.append(' %s' % key)
            else:
                attributes.append(' %s="%s"' % (key, value))
        return '<%s%s>' % (self.tag, ''.join(attributes))

    def closing_tag(self):
        return '</%s>' % self.tag

    def append_child(self, node):
        self.children.append(node)
        return self

    def add_class(self, newclass):
        classes = self.attributes.get('class', '').split()
        if newclass not in classes:
            classes.append(newclass)
            self.attributes['class'] = ' '.join(sorted(classes))


# Text nodes contain only text. They have no children.
class TextNode(Node):

    def __init__(self, text):
        Node.__init__(self)
        self.text = text

    def render(self, meta):
        return inline.render(self.text, meta) + '\n'


# Comment nodes represent HTML comments.
class CommentNode(Node):

    def render(self, meta):
        html = []
        html.append('<!--\n')
        html.append(self.text.rstrip())
        html.append('\n')
        html.append('-->\n')
        return ''.join(html)


# Insert nodes provide a mechanism for inserting generated content,
# e.g. tables of contents or footnotes.
class InsertNode(Node):

    def render(self, meta):
        if self.text in meta:
            return meta[self.text].render(meta)
        else:
            sys.stderr.write('Error: missing insert %s.\n' % repr(self.text))
            return ''


# Turns on newline-to-linebreak mode for all children.
class LinebreakNode(Node):

    def render(self, meta):
        context = meta.setdefault('context', [])
        context.append('nl2br')
        rendered = ''.join(child.render(meta) for child in self.children)
        context.pop()
        return rendered
