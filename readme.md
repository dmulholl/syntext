
# Syntex

Syntex is a lightweight, markdownish markup language for generating HTML. It's implemented in Python and can be used as both a command line utility and a Python library.

On the command line:

    $ syntex < input.txt > output.html

As a library:

    >>> import syntex
    >>> html = syntex.render(text)

Syntex inherits much of its basic syntax from Markdown:

    This is a paragraph containing *emphasised* and **strong** text.
    It also contains `code` in backticks.

    This is a second paragraph containing a [link](http://example.com).

Syntex differs from Markdown in providing an extensible, indentation-based syntax for generating arbitrary HTML:

    :tag [keyword] [.class] [#id] [&attr] [attr="value"]
        block content
        block content
        ...

Syntex also includes out-of-the-box support for tables, tables-of-contents, definition lists, syntax highlighting, and footnotes.

See the package's [documentation](http://mulholland.xyz/docs/syntex/) for further details.


## Installation

Install directly from the Python Package Index using `pip`:

    $ pip install syntex

Syntex requires Python 3.4 or later.


## License

This work has been placed in the public domain.
