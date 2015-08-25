"""
This sample extension prints a simple status report at the end of each build.

Author: Darren Mulholland <dmulholland@outlook.ie>
License: Public Domain

"""

from ark import hooks, site


# Register a callback on the 'exit' event hook to print our status report.
@hooks.register('exit')
def print_status_report():
    rendered, written = site.page_count()
    time = site.build_time()
    average = time / (rendered or 1)
    status = "%s pages rendered, %s pages written in %.2f seconds. "
    status += "%.4f seconds per page."
    print(status % (rendered, written, time, average))
