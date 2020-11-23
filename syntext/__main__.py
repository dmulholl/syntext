# ---------------------------------------------------------
# This module makes the package directly executable. To
# run a syntext package located on Python's import search
# path:
#
#   $ python -m syntext
#
# To run an arbitrary syntext package:
#
#   $ python /path/to/syntext/package
#
# ---------------------------------------------------------

import os
import sys


# Python doesn't automatically add the package's parent directory to the
# module search path so we need to do so manually before we can import
# syntext.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


import syntext
syntext.main()
