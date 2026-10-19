#!/usr/bin/env python3
"""Compatibility wrapper for the package-based ANIOXAZ app."""

from __future__ import annotations

from anioxaz.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
