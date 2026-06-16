"""ConfigLoadingService: load the rollup spec and guard its schema version.

The service asks the injected ``ConfigProvider`` for both the spec and the
schema version it expects, then refuses to proceed when the spec it loaded
declares a different version. This stops a stale or mismatched taxonomy
from silently producing a wrong debrief.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from o7debrief.application.errors import ConfigSchemaMismatchError

if TYPE_CHECKING:
    from o7debrief.application.ports.config_provider import ConfigProvider
    from o7debrief.domain.rules.rollup_spec import RollupSpec

__all__ = ["ConfigLoadingService"]


class ConfigLoadingService:
    """Loads the rollup specification, enforcing schema-version agreement.

    The injected ``config_provider`` (a port) and the ``RollupSpec`` it
    returns are named as forward references so this module imports only the
    application layer; the spec is used purely by reading its attributes.
    """

    def __init__(self, config_provider: ConfigProvider) -> None:
        self._config_provider = config_provider

    def load_spec(self) -> RollupSpec:
        """Return the spec, raising if its version is not the expected one."""
        expected = self._config_provider.schema_version()
        spec = self._config_provider.load()
        if spec.schema_version != expected:
            raise ConfigSchemaMismatchError(expected, spec.schema_version)
        return spec
