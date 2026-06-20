from __future__ import annotations

from importlib.resources import files
from pathlib import PurePosixPath


def read_render_asset(relative_path: str) -> str:
    """Read a packaged frontend asset relative to ``scalpel/render``."""
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"invalid render asset path: {relative_path!r}")

    resource = files("scalpel.render")
    for part in path.parts:
        resource = resource.joinpath(part)
    try:
        return resource.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError) as ex:
        raise RuntimeError(f"failed to load packaged render asset: {relative_path}") from ex


__all__ = ["read_render_asset"]
