from __future__ import annotations

import sys

from typing import Sequence


class DefinitionError(RuntimeError):
    # Eliminate the output of traceback before our custom error message prints out
    sys.tracebacklimit = 0

    def __init__(self, msg: str, path: Sequence[str | int] | None = None):
        super(DefinitionError, self).__init__("%s" % msg)
        self.msg = msg
        self.path = path
