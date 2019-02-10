---
title: Inline Syntax
---

Syntext shares most of its inline markup syntax with Markdown.


### Formatting

Single asterisks indicate italic text, double asterisks indicate bold text, triple asterisks indicate bold italic text:

    This text is *italic*.
    This text is **bold**.
    This text is ***bold and italic***.

Backticks are used to enclose code samples:

    This is a `code sample`.

HTML in code samples is automatically escaped.



### Links

Link syntax is borrowed directly from Markdown. Title text can optionally be specified after the url:

    [link text](http://example.com title text)

Syntext also supports Markdown-style reference links:

    [link text][reference]

Link references can be specified anywhere in the document. They take one of the following forms:

    \[reference]: http://example.com
        optional title text

    \[reference]:
        http://example.com
        optional title text

If the reference text is omitted from the link, the link text will be used instead when searching for link references.



### Images

Image syntax is borrowed directly from Markdown. Title text can optionally be specified after the url:

    ![alt text](http://example.com/image.jpg title text)

Syntext also supports Markdown-style reference images:

    ![alt text][reference]

Image references can be specified anywhere in the document. Their form is identical to that of link references. If the reference text is omitted from the image, the alt text will be used instead when searching for references.



### HTML

Syntext ignores inline HTML tags so it's fine to mix and match inline HTML and Syntext markup.

The HTML syntax characters `<`, `>`, and `&` are automatically escaped unless they form part of a HTML tag or character entity.



### Dashes

Double hyphens `--` are converted into en-dashes `&ndash;`; triple hyphens are converted into em-dashes `&mdash;`.
