# ------------------------------------------------------------------------------
# This module makes the `monk` package directly executable.
#
# To run a `monk` package located on Python's import search path:
#
#   $ python -m monk
#
# To run an arbitrary `monk` package:
#
#   $ python /path/to/monk/package
#
# This latter form can be used for running development versions of Monk.
# ------------------------------------------------------------------------------

import os
import sys


# Python doesn't automatically add the package's parent directory to the
# module search path so we need to do so manually before we can import `monk`.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


import monk
monk.main()
