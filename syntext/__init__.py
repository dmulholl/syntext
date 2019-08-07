# ---------------------------------------------------------
# Syntext: a lightweight, markdownish markup language.
#
# Author: Darren Mulholland <dmulholl@tcd.ie>
# License: Public Domain
# ---------------------------------------------------------

# Package version number.
__version__ = "2.0.0"

from .interface import render
from .interface import main
from .utils import Error

from . import tags
from . import nodes
from . import parsers
from . import escapes
from . import utils
from . import shorthand

