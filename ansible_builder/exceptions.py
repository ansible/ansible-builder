import sys

from .colors import MessageColors


class DefinitionError(RuntimeError):
    # Eliminate the output of traceback before our custom error message prints out
    sys.tracebacklimit = 0

    def __init__(self, msg):
        super(DefinitionError, self).__init__(MessageColors.FAIL + ("%s" % msg) + MessageColors.ENDC)
        self.msg = msg
