#!/usr/bin/env python3
"""Entry point for the o7Debrief setup program.

The setup program is a package rather than a single script, so its entry point
sits at the repository root beside main.py. Running a script inside the package
directory would put that directory on the module search path instead of the
root, and the ``installer.*`` imports would not resolve; compiling from here
gives Nuitka the same layout it reproduces in the bundle, so one rule holds in
both source and compiled runs.

    python installer_main.py            run the setup window from source
    python installer_main.py --uninstall  run the uninstall flow

buildinstaller.py compiles this file. British spelling is used in comments. No
em dashes appear anywhere.
"""

from __future__ import annotations

from installer import main

if __name__ == "__main__":
    raise SystemExit(main())
