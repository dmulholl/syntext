---
title: Miscellanea
---


### Escapes

The following characters can be escaped by a preceding backslash:

    ! " # $ % & \ ' ( ) * + , - . / : ; < = > ? @ [ ] ^ _ ` { | } ~ •

Escaped characters lose any special significance they might otherwise have.



### Tables of Contents

Syntext can automatically generate a table of contents for a document. This table can be inserted using the `insert` tag:

    :insert toc

The default listing skips H1 headings to avoid including the document title itself. A full listing of all the document's headings can be inserted using the `fulltoc` keyword:

    :insert fulltoc

The table of contents is generated as an unordered list of links.



### Footnotes

Syntext includes built-in support for footnotes:

    This sentence ends with a footnote reference.[^1]

Footnote references can omit their index to take advantage of automatic numbering:

    This sentence ends with an automatically-numbered
    reference.[^]

Footnotes themselves can be specified anywhere in the document using the `footnote` tag:

    :footnote 1
        This is a footnote. It can contain any kind of
        block-level markup.

Footnotes can also omit their index to take advantage of automatic numbering:

    :footnote
        This is an automatically-numbered footnote.

Note that footnote indices do not have to be numeric. Any sequence of non-whitespace characters can be used.

You can specify the insertion point for your footnotes using the `:insert` tag:

    :insert footnotes

Footnote references are wrapped in the following markup:

::: html

    <sup class="footnote-ref" id="footnote-ref-123">
        <a href="#footnote-123">123</a>
    </sup>

Footnotes are wrapped in the following markup:

::: html

    <div class="footnote" id="footnote-123">
        <div class="footnote-index">
            <a href="#footnote-ref-123">123</a>
        </div>
        <div class="footnote-body"> ... </div>
    </div>

Each footnote is backlinked to its reference in the document.



### Extensions

Syntext can easily be extended to support custom tags.

To create a new custom tag, register its handler function using the `@tags.register()` decorator:

::: python

    import syntext

    @syntext.tags.register('tag')
    def handler(tag, pargs, kwargs, content, meta):
        ...
        return node

See the `syntext/tags.py` file for numerous examples to follow.

By convention, custom tag names are prefixed with a colon, i.e. the custom tag `foo` should be registered as `":foo"`. The tag can then be used with a double colon:

    ::foo
        block content
        ...

This convention makes custom tags easy to identify and prevents potential name clashes as new builtin tags are added over time.
