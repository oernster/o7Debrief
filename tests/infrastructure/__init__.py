"""Integration tests for the infrastructure adapters.

These exercise the concrete adapters against real files in a temporary
directory and the real taxonomy, so the file format, TOML parsing, JSON
persistence and rendering are all proven end to end. The pure layers are
covered by the gated unit tests; infrastructure is integration-tested here.
"""

from __future__ import annotations
