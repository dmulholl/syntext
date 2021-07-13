# ------------------------------------------------------------------------------
# Escape functions for backslashed characters in input text.
# ------------------------------------------------------------------------------

import re


# The following characters in input text can be escaped with a backslash.
escapeables = '`*.:#+\\-•|'


# Placeholders to substitute for escaped characters during preprocessing.
stx = '\x02'
etx = '\x03'
esc2char = {'%s%s%s' % (stx, ord(c), etx): c for c in escapeables}
char2esc = {c: '%s%s%s' % (stx, ord(c), etx) for c in escapeables}


# Replaces backslashed characters in input text with escaped placeholders.
def escapechars(text):

    def callback(match):
        char = match.group(1)
        if char in escapeables:
            return '%s%s%s' % (stx, ord(char), etx)
        else:
            return match.group(0)

    return re.sub(r"\\(.)", callback, text, flags=re.DOTALL)


# Replaces escaped placeholders with their corresponding characters.
def unescapechars(text):
    for key, value in esc2char.items():
        text = text.replace(key, value)
    return text
