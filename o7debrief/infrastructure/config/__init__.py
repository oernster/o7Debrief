"""Configuration adapters: parse the taxonomy into a domain RollupSpec.

The public adapter is ``TomlConfigProvider`` (see ``toml_config_provider``),
which reads ``config/debrief_taxonomy.toml`` with the standard-library tomllib
module and builds the domain ``RollupSpec`` the application depends on.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations
