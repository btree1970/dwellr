#!/usr/bin/env -S uv run python
"""Dwell CLI entry point."""

import sys

from cli.main import main

if __name__ == "__main__":
    sys.exit(main())
