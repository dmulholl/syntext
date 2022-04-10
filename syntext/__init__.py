# ---------------------------------------------------------
# Syntext: a lightweight, markdownish markup language.
# ---------------------------------------------------------

__version__ = "3.1.2"

from .interface import render
from .interface import main
from .utils import SyntextError

from . import tags
from . import nodes
from . import parsers
from . import utils
from . import shorthand
