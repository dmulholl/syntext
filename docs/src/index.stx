---
title: Home
meta title: Monk &mdash; a markdownish markup language
---

Monk is a lightweight, markdownish markup language for generating HTML. It's implemented in Python and can be used as both a command line utility and a Python library.

When used on the command line Monk reads from `stdin` and prints to `stdout`:

    $ monk < input.txt > output.html

To use Monk as a Python library call its `render()` function with a string of input:

::: python

    >>> import monk
    >>> html = monk.render(text)



### Overview

Monk shares much of its basic syntax with Markdown:

    This paragraph contains *italic* and **bold** text.
    It also contains a `code sample` in backticks.

    This paragraph contains a [link](http://example.com).

Monk differs from Markdown in supporting an extensible, indentation-based syntax for generating arbitrary HTML:

    :div .outer
        :div .inner
            This is a paragraph.

Monk also includes out-of-the-box support for tables, tables-of-contents, definition lists, syntax highlighting, and footnotes.



### Installation

Install directly from the Python Package Index using `pip`:

    $ pip install libmonk

Monk requires Python 3.4 or later.



### Command Line Interface

Use the `monk --help` flag to view the utility's command line help:

    Usage: monk [FLAGS]

      Renders input text in Monk format into HTML. Reads
      from stdin and prints to stdout.

      Example:

          $ monk < input.txt > output.html

    Flags:
      -d, --debug       Run in debug mode.
      -h, --help        Print the application's help text.
      -p, --pygmentize  Add syntax highlighting to code.
      -v, --version     Print the application's version.

Monk can use the [Pygments][] package to add syntax highlighting to code blocks; this feature can be enabled via the `--pygmentize` flag. (Pygments is installed automatically when you install Monk using `pip`).

Only code blocks with a language attribute will have syntax highlighting applied.

[pygments]: http://pygments.org/



### Links

* [Github Homepage](https://github.com/dmulholland/monk)
* [Python Package Index](https://pypi.python.org/pypi/libmonk/)
* [Online Documentation](http://mulholland.xyz/docs/monk/)



### License

This work has been placed in the public domain.
