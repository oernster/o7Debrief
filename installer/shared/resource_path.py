"""Locating the data the setup program carries.

The payload is anchored on the ``installer`` package directory rather than on
the running executable, so one rule holds in both modes:

- from source, the package directory is ``<repo>/installer`` and the payload
  staged by buildinstaller.py sits at ``<repo>/installer/payload``;
- compiled, Nuitka reproduces the package layout under the unpacked root and
  buildinstaller.py includes the same data at ``installer/payload``.

Anchoring on ``__file__`` of the main script would not survive the entry point
moving, which is why the anchor is the package itself. British spelling is used
in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from pathlib import Path


def installer_root() -> Path:
    """Return the ``installer`` package directory in source and compiled runs."""
    return Path(__file__).resolve().parents[1]


def program_root() -> Path:
    """Return the directory containing the installer package.

    This is the repository root from source and the unpacked bundle root when
    compiled. Data files included at the top level rather than under the
    package are found here.
    """
    return installer_root().parent
