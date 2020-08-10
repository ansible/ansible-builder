import sys

from .colors import MessageColors


class DefinitionError(RuntimeError):
    sys.tracebacklimit = 0

    def __init__(self, msg):
        super(DefinitionError, self).__init__(MessageColors.FAIL + ("%s" % msg) + MessageColors.ENDC)
        self.msg = msg
