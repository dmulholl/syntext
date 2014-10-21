
Syntex
======

Syntex is (yet another) lightweight markup language for generating HTML from plain text. It's implemented in Python 3 and can be used both as a command line script and as a Python library.

On the command line:

    $ syntex < input.txt > output.html

As a Python library:

    import syntex
    html, meta = syntex.render(text)


Rationale
---------

Syntex scratches a personal itch, being intended as an easy-to-parse, extensible alternative to Markdown. It borrows most of its basic inline syntax from Markdown:

    This is a paragraph containing *emphasised* and **strong** text.
    It also contains a `code sample` in backticks.

    This second paragraph contains a [link](http://example.com).

Syntex differs from Markdown in using an extensible, indentation-based syntax for block-level elements:

    :tag [keyword] [.class1 .class2] [#id] [attr1=foo attr2="bar"]
        block content
        block content

        block content
        ...

It also includes out of the box support for document metadata, tables, tables-of-contents, syntax highlighting, and footnotes.


Installation
------------

Syntex can be installed directly from the Python Package Index using `pip`:

    $ pip install syntex

Syntex requires Python 3.2 or later.


Dependencies
------------

Syntex will use the [PyYAML](http://pyyaml.org) module if available to parse document metadata and the [Pygments](http://pygments.org) module if available to add syntax highlighting to code samples.


Status
------

Syntex is a pre-1.0 work-in-progress. Future releases may contain backwards-compatibility breaking changes.


License
-------

This work has been placed in the public domain.
