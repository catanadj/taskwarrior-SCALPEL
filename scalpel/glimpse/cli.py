from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scalpel-glimpse",
        description="Read-only terminal calendar view for SCALPEL.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="scalpel-glimpse (foundation)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    raise SystemExit("scalpel-glimpse rendering is not available yet")


if __name__ == "__main__":
    raise SystemExit(main())
