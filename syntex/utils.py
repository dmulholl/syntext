# -------------------------------------------------------------------------
# Utiltiy functions and classes.
# -------------------------------------------------------------------------

import re
import unicodedata

from . import escapes


# Makes input text available as a stream of lines. Strips newlines.
class LineStream:

    # A stream can be initialized with a string or a list of lines.
    def __init__(self, arg=None):
        if isinstance(arg, str):
            text = escapes.escapechars(arg)
            text = text.expandtabs(4)
            self.lines = [line.rstrip() for line in text.splitlines()]
        else:
            self.lines = arg or []
        self.index = 0

    def __str__(self):
        return '\n'.join(self.lines[self.index:])

    # Appends a line to the end of the stream.
    def append(self, line):
        self.lines.append(line)
        return self

    # Prepends a line to the beginning of the stream.
    def prepend(self, line):
        self.lines.insert(0, line)

    # Strips the common leading indent from all lines in the stream.
    def dedent(self):

        def countspaces(line):
            for index, char in enumerate(line):
                if char != ' ':
                    return index

        mindent = min((countspaces(l) for l in self.lines if l), default=0)

        for index, line in enumerate(self.lines):
            if line:
                self.lines[index] = line[mindent:]

        return self

    # Indents all non-blank lines in the stream by n spaces.
    def indent(self, n=4):
        for index, line in enumerate(self.lines):
            if line:
                self.lines[index] = ' ' * n + line
        return self

    # Strips leading and trailing blank lines.
    def trim(self):
        while self.lines and self.lines[0] == '':
            self.lines.pop(0)
        while self.lines and self.lines[-1] == '':
            self.lines.pop()
        return self

    # Returns the next item in the stream without consuming it.
    def peek(self):
        return self.lines[self.index]

    # Consumes and returns the next item in the stream.
    def next(self):
        self.index += 1
        return self.lines[self.index - 1]

    # Rewinds the stream index by n lines.
    def rewind(self, n):
        self.index -= n

    # Returns true if the stream contains at least one more item.
    def has_next(self):
        return self.index < len(self.lines)

    # Returns true if the stream ends with one or more blank lines.
    def has_trailing_blank(self):
        if self.lines and self.lines[-1] == '':
            return True
        return False

    # Returns true if the stream contains at least one blank line.
    def contains_blank(self):
        for line in self.lines:
            if line == '':
                return True
        return False


# Formats title text for output on the command line.
def title(text, w=80):
    return '=' * w + '\n' + text.center(w, '-') + '\n' +  '=' * w + '\n'


# Strips all angle-bracket-enclosed substrings.
def strip_tags(text):
    return re.sub(r'<[^>]*>', '', text)


# Processes a string for use as an #id.
def idify(s):
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('ascii')
    s = s.lower()
    s = s.replace("'", '')
    s = re.sub(r'[^a-z0-9-]+', '-', s)
    s = re.sub(r'--+', '-', s).strip('-')
    s = re.sub(r'^\d+', '', s)
    return s or 'id'
