# ---------------------------------------------------------
# Syntext: a lightweight, markdownish markup language.
# ---------------------------------------------------------

# Package version number.
__version__ = "2.8.2"

from .interface import render
from .interface import main
from .utils import SyntextError

from . import tags
from . import nodes
from . import parsers
from . import escapes
from . import utils
from . import shorthand
