# --------------------------------------------------------------------------
# Syntex: a lightweight, markdownish markup language.
#
# Author: Darren Mulholland <darren@mulholland.xyz>
# License: Public Domain
# --------------------------------------------------------------------------

from .interface import render
from .interface import main

from . import tags
from . import nodes
from . import parsers
from . import escapes
from . import utils
