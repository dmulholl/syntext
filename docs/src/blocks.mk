---
title: Block Syntax
---

Monk supports two kinds of block-level markup: custom syntax for common elements and generic syntax for generating arbitrary HTML. Syntax for common elements is described below.



### Paragraphs

A paragraph is a group of adjacent lines separated by one or more blank lines:

    This is a paragraph. Note that it includes
    all adjacent lines of text.

    This is a second paragraph.



### Headings

H1 headings can be enclosed in equals signs `=`:

    ==========
    H1 Heading
    ==========

H2 headings can be enclosed in dashes `-`:

    ----------
    H2 Heading
    ----------

In each case the upper line of symbols is optional. The text can extend over multiple lines as long as it does not include any blank lines:

    ------
     Some
     Text
    ------

Headings can also be indicated by prefacing their text with an appropriate number of hash symbols `#`:

    ### H3 Heading ###

The trailing symbols in the example above are optional and can be omitted.



### Ordered and Unordered Lists

Lists come in *compact* and *block* varieties. A *compact* list is a list whose elements are not separated by blank lines. List items in a compact list will not be wrapped in paragraph tags in the HTML output.

An unordered list can use either an asterisk `*`, dash `-`, plus-symbol `+`, or unicode bullet-symbol `\u2022` as its list-item marker:

    * foo           - foo           + foo           • foo
    * bar           - bar           + bar           • bar
    * baz           - baz           + baz           • baz

An ordered list uses either integer-period `<int>.` or hash-period `#.` as its list-item marker:

    1. foo         #. foo
    2. bar         #. bar
    3. baz         #. baz

Ordered lists are numbered according to their opening integer:

    5. This list starts.
    6. With list item 5.

List-item markers can be indented by up to three spaces. A list-item consists of its opening line plus all subsequent blank or indented lines:

    * This list item is split
      over two lines.

List items can contain nested compact lists:

    * foo
      1. bar
      2. baz
    * bam

Note that switching to a different list-item marker will begin a new list, i.e. the following markup will create two separate lists each containing a single item:

    - foo
    + bar

A *block* list is a list whose elements are separated by one or more blank lines.

    * This is a block list.

    * With two elements.

Each list-item is parsed as a new block-level context and can contain any number of block-level elements, including paragraphs, headings, and nested lists.

    * This list item contains a paragraph and a compact list.

      1. foo
      2. bar

    * This list item contains two paragraphs. This is the first.

      And this is the second.

List-item markers can be indented by up to three spaces. A list-item consists of its opening line plus all subsequent blank or indented lines.

Note that a list consisting of a single item will always be treated as a block list.



### Definition Lists

Monk supports definition lists with terms enclosed in double pipes:

    ||  Term 1  ||

        This is the definition of the first term.

    ||  Term 2  ||

        This is the definition of the second term.

A term's definition consists of all subsequent blank or indented lines and can contain any number of block-level elements.



### Code Blocks

A block of text indented by one tab or four spaces is treated as a code block and wrapped in `<pre>` tags in the HTML output. The code block can contain blank lines and is ended by the first non-indented line.

    This paragraph is followed by a code block.

        <p>Hello world!</p>

The language can be specified using a `:pre` [tag][pre]:

    ::: python

        print("hello world")

HTML in code blocks is automatically escaped.

[pre]: @root/tags//#pre


### Horizontal Rules

A line containing three or more `*` or `-` characters (optionally separated by spaces) will produce a horizontal rule:

    * * *
    -----



### Raw HTML

Monk can recognise and ignore block-level HTML in its input so you can freely mix and match Monk markup and raw HTML.

Monk uses two simple rules for identifying block-level HTML:

* A single line beginning with an opening block-level tag and ending with
  its corresponding closing tag, e.g.

      <div><p>This is raw HTML and will be left untouched.</p></div>

* An opening block-level tag followed *vertically below* by its corresponding closing
  tag, e.g.

      <div>
        <p>This is raw HTML and will be left untouched.</p>
      </div>

The opening and closing tags should not be indented *relative to their context* but can be freely mixed with other block-level Monk elements, e.g.

    :div .outer
        This is a paragraph.

        <div class="inner">
            <p>This is raw HTML.</p>
        </div>

        This is another paragraph.

Note that inline Monk formatting will not be processed inside block-level HTML.