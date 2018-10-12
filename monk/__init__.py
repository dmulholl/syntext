# ------------------------------------------------------------------------------
# Monk: a lightweight, markdownish markup language.
#
# Author: Darren Mulholland <darren@mulholland.xyz>
# License: Public Domain
# ------------------------------------------------------------------------------

# Package version number.
__version__ = "1.2.2"

from .interface import render
from .interface import main

from . import tags
from . import nodes
from . import parsers
from . import escapes
from . import utils
