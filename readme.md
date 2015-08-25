
Syntex
======

Syntex is a lightweight, markdownish markup language for generating HTML from plain text. It's implemented in Python 3 and can be used both as a command line script and a Python library.

Syntex borrows most of its basic syntax from Markdown:

    This is a paragraph containing *emphasised* and **strong** text.
    It also contains `code` in backticks.

    This is a second paragraph containing a [link](http://example.com).

Syntex differs from Markdown in using an extensible, indentation-based syntax for block-level elements:

    :tag [keyword] [.class1 .class2] [#id] [attr1=foo attr2="bar"]
        block content
        ...

Syntex also includes out of the box support for document metadata, tables, tables-of-contents, definition lists, syntax highlighting, and footnotes.

See the package's [documentation](http://pythonhosted.org/syntex/) for further details.



Installation
------------

Install directly from the Python Package Index using `pip`:

    $ pip install syntex

Syntex requires Python 3.2 or later.



License
-------

This work has been placed in the public domain.
