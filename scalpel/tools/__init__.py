"""scalpel.tools package

Developer utilities (smoke builds, fixture tools, CI gate, etc.).

Design note:
  Keep this package's __init__ free of eager imports to avoid side-effects at
  import time (important for module execution via `python -m ...`).
"""

__all__: list[str] = []
