# --------------------------------------------------------------------------
# This module makes the `syntex` package directly executable.
#
# To run a `syntex` package located on Python's import search path:
#
#   $ python -m syntex
#
# To run an arbitrary `syntex` package:
#
#   $ python /path/to/syntex/package
#
# This latter form can be used for running development versions of Syntex.
# --------------------------------------------------------------------------

import os
import sys


# Python doesn't automatically add the package's parent directory to the
# module search path so we need to do so manually before we can import `syntex`.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


import syntex
syntex.main()
