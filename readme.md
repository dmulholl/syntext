
# Syntext

Syntext is a lightweight, markdownish markup language for generating HTML. It's implemented in Python and can be used as both a command line utility and a Python library.

On the command line:

    $ syntext < input.txt > output.html

As a library:

    >>> import syntext
    >>> html = syntext.render(text)

Syntext inherits much of its basic syntax from Markdown:

    This is a paragraph containing *emphasised* and **strong** text.
    It also contains `code` in backticks.

    This is a second paragraph containing a [link](http://example.com).

Syntext differs from Markdown in supporting an extensible, indentation-based syntax for generating arbitrary HTML:

    :div .outer
        :div .inner
            This is a paragraph.

Syntext also includes out-of-the-box support for tables, tables-of-contents, definition lists, syntax highlighting, and footnotes.

See the [documentation](https://darrenmulholland.com/docs/syntext/) for details.
