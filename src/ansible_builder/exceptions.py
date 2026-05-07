from __future__ import annotations

import sys

from typing import Sequence


class DefinitionError(RuntimeError):
    """
    Represents a custom runtime error for definition-related issues.

    This class is designed to handle and customize error messages specifically for
    definition errors, such as invalid configurations or missing definitions. It also
    suppresses the traceback output for cleaner error handling.
    """
    sys.tracebacklimit = 0

    def __init__(self, msg: str, path: Sequence[str | int] | None = None):
        super().__init__(f"{msg}")
        self.msg = msg
        self.path = path
