# ------------------------------------------------------------------------------
# Table of Contents builder.
# ------------------------------------------------------------------------------

from . import nodes
from . import utils


# Table of Contents Builder
#
# Processes a tree of block elements to produce a table of contents with links
# to each heading in the document. Note that this process modifies the tree in
# place by adding an automatically generated ID to any heading element that
# lacks one.
#
# The table is returned as a Node tree representing an unordered list with
# nested sublists.
#
#     toc = TOCBuilder(root).toc()
#
class TOCBuilder:

    def __init__(self, node):
        self.root = dict(level=0, text='ROOT', id='', subs=[])
        self.stack = [self.root]
        self.ids = []
        self._process_node(node)

    def _process_node(self, node):
        if node.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            heading = self._make_toc_node(node)
            while heading['level'] <= self.stack[-1]['level']:
                self.stack.pop()
            self.stack[-1]['subs'].append(heading)
            self.stack.append(heading)
        else:
            for child in node.children:
                self._process_node(child)

    def _make_toc_node(self, node):
        level = int(node.tag[1])
        html = node.render({})
        text = utils.strip_tags(html).strip()
        if 'id' in node.attributes:
            id = node.attributes['id']
        else:
            index = 2
            slug = utils.idify(text)
            id = slug
            while id in self.ids:
                id = '%s-%s' % (slug, index)
                index += 1
            node.attributes['id'] = id
        self.ids.append(id)
        return dict(level=level, text=text, id=id, subs=[])

    # Returns the table of contents as an unordered list. Skips over root-level
    # H1 headings.
    def toc(self):
        ul = nodes.Node('ul', {'class': 'stx-toc'})
        for node in self.root['subs']:
            if node['level'] == 1:
                for subnode in node['subs']:
                    ul.append_child(self._make_li_node(subnode))
            else:
                ul.append_child(self._make_li_node(node))
        return ul

    # Returns the table of contents as an unordered list. Includes root-level
    # H1 headings.
    def fulltoc(self):
        ul = nodes.Node('ul', {'class': 'stx-toc'})
        for node in self.root['subs']:
            ul.append_child(self._make_li_node(node))
        return ul

    def _make_li_node(self, node):
        li = nodes.Node('li')
        li.append_child(nodes.TextNode('[%s](#%s)' % (node['text'], node['id'])))
        if node['subs']:
            ul = nodes.Node('ul')
            li.append_child(ul)
            for child in node['subs']:
                ul.append_child(self._make_li_node(child))
        return li
