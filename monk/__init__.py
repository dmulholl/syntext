# ------------------------------------------------------------------------------
# Monk: a lightweight, markdownish markup language.
#
# Author: Darren Mulholland <dmulholl@tcd.ie>
# License: Public Domain
# ------------------------------------------------------------------------------

# Package version number.
__version__ = "1.3.2"

from .interface import render
from .interface import main

from . import tags
from . import nodes
from . import parsers
from . import escapes
from . import utils
