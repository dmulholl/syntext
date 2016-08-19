# -------------------------------------------------------------------------
# Functions for parsing and rendering inline markup.
# -------------------------------------------------------------------------

import html
import hashlib
import re


# -------------------------------------------------------------------------
# Regular expressions for identifying inline markup.
# -------------------------------------------------------------------------


# **foo bar**
re_strong = re.compile(r"\*{2}(\S.*?\S)\*{2}")

# *foo bar*
re_emphasis = re.compile(r"\*(\S.*?\S)\*")

# `foo bar`
re_backticks = re.compile(r"`(.+?)`")

# [link text](http://example.com optional title text)
re_link = re.compile(r"\[([^\]]+)\]\(([^\)]+)\)")

# [link text][ref]
re_ref_link = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")

# ![alt text](http://example.com optional title text)
re_img = re.compile(r"!\[([^\]]*)\]\(([^\)]+)\)")

# ![alt text][ref]
re_ref_img = re.compile(r"!\[([^\]]*)\]\[([^\]]*)\]")

# [^ref] or [^]
re_footnote = re.compile(r"\[\^([^\]]*)\]")

# &amp; &#x27;
re_entity = re.compile(r"&[#a-zA-Z0-9]+;")

# html tags: <span>, </span>, <!-- comment -->, etc.
re_html = re.compile(r"<([a-zA-Z/][^>]*?|!--.*?--)>")

# <http://example.com>
re_bracketed_url = re.compile(r"<((?:https?|ftp)://[^>]+)>")

# http://example.com
re_bare_url = re.compile(r"""
    (^|\s)
    (https?|ftp)
    (://[-A-Z0-9+&@#/%?=~_|\[\]\(\)!:,\.;]*[-A-Z0-9+&@#/%=~_|\[\]])
    ($|\W)
    """, re.VERBOSE | re.MULTILINE | re.IGNORECASE)


# -------------------------------------------------------------------------
# Renderers.
# -------------------------------------------------------------------------


# Entry point.
def render(text, meta):
    hashes = {}

    text = render_backticks(text, hashes)
    text = render_bracketed_urls(text, hashes)
    text = render_inline_html(text, hashes)
    text = render_html_entities(text, hashes)

    text = html.escape(text, False)

    text = render_strong(text)
    text = render_emphasis(text)
    text = render_images(text)
    text = render_ref_images(text, meta)
    text = render_links(text)
    text = render_ref_links(text, meta)
    text = render_footnotes(text, meta)

    if 'nl2br' in meta.get('context', []):
        text = text.replace('\n', '<br>\n')

    for key, value in hashes.items():
        text = text.replace(key, value)

    return text + '\n'


# Hashes a string, stores it as a {digest: string} pair in 'hashes', and
# returns the digest.
def hashstr(text, hashes):
    digest = hashlib.sha1(text.encode()).hexdigest()
    hashes[digest] = text
    return digest


def render_backticks(text, hashes):
    def callback(match):
        content = html.escape(match.group(1), False)
        return hashstr('<code>%s</code>' % content, hashes)
    return re_backticks.sub(callback, text)


def render_bracketed_urls(text, hashes):
    def callback(match):
        url = '<a href="%s">%s</a>' % (match.group(1), match.group(1))
        return hashstr(url, hashes)
    return re_bracketed_url.sub(callback, text)


def render_inline_html(text, hashes):
    return re_html.sub(lambda match: hashstr(match.group(), hashes), text)


def render_html_entities(text, hashes):
    return re_entity.sub(lambda match: hashstr(match.group(), hashes), text)


def render_strong(text):
    return re_strong.sub(r"<strong>\1</strong>", text)


def render_emphasis(text):
    return re_emphasis.sub(r"<em>\1</em>", text)


def render_images(text):
    def callback(match):
        alt = html.escape(match.group(1))
        atts = match.group(2).strip().split(' ', maxsplit=1)
        url = atts[0]
        title = html.escape(atts[1] if len(atts) > 1 else '').strip()
        if title:
            return '<img alt="%s" src="%s" title="%s">' % (alt, url, title)
        else:
            return '<img alt="%s" src="%s">' % (alt, url)
    return re_img.sub(callback, text)


def render_ref_images(text, meta):
    def callback(match):
        alt = html.escape(match.group(1))
        ref = match.group(2).lower() if match.group(2) else alt.lower()
        url, title = meta.get('linkrefs', {}).get(ref, ('', ''))
        if title:
            title = html.escape(title)
            return '<img alt="%s" src="%s" title="%s">' % (alt, url, title)
        else:
            return '<img alt="%s" src="%s">' % (alt, url)
    return re_ref_img.sub(callback, text)


def render_links(text):
    def callback(match):
        text = match.group(1)
        atts = match.group(2).strip().split(' ', maxsplit=1)
        url = atts[0]
        title = html.escape(atts[1] if len(atts) > 1 else '').strip()
        if title:
            return '<a href="%s" title="%s">%s</a>' % (url, title, text)
        else:
            return '<a href="%s">%s</a>' % (url, text)
    return re_link.sub(callback, text)


def render_ref_links(text, meta):
    def callback(match):
        text = match.group(1)
        ref = match.group(2).lower() if match.group(2) else text.lower()
        url, title = meta.get('linkrefs', {}).get(ref, ('', ''))
        if title:
            title = html.escape(title)
            return '<a href="%s" title="%s">%s</a>' % (url, title, text)
        else:
            return '<a href="%s">%s</a>' % (url, text)
    return re_ref_link.sub(callback, text)


def render_footnotes(text, meta):
    def callback(match):
        if match.group(1):
            ref = match.group(1)
        else:
            ref = meta.setdefault('footnote-ref-index', 1)
            meta['footnote-ref-index'] += 1
        fmstr = '<sup class="footnote-ref"><a href="#footnote-%s">%s</a></sup>'
        return fmstr % (ref, ref)
    return re_footnote.sub(callback, text)
