# scalpel/util/console.py
from __future__ import annotations
import sys
from typing import Any

def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)

