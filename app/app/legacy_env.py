"""Accept the old ``CELESTIA_`` environment prefix for one deprecation cycle.

Settings moved to the ``COMPLIANCEOS_`` prefix. For each ``CELESTIA_*`` variable whose
``COMPLIANCEOS_*`` twin is unset, copy the value across and warn once, naming the old variables. A
``COMPLIANCEOS_*`` value that is already set always wins. Runs from ``app/__init__.py`` so it takes
effect before any module reads the environment. Values in a ``.env`` file are not translated.
"""

from __future__ import annotations

import logging
import os
from collections.abc import MutableMapping

OLD_PREFIX = "CELESTIA_"
NEW_PREFIX = "COMPLIANCEOS_"

log = logging.getLogger("complianceos.config")


def apply_legacy_env(environ: MutableMapping[str, str] | None = None) -> list[str]:
    """Copy unset ``COMPLIANCEOS_*`` values from ``CELESTIA_*``. Returns the old names used."""
    env = os.environ if environ is None else environ
    used: list[str] = []
    for name in sorted(k for k in env if k.startswith(OLD_PREFIX)):
        new = NEW_PREFIX + name[len(OLD_PREFIX):]
        if new not in env:
            env[new] = env[name]
            used.append(name)
    if used:
        log.warning(
            "deprecated environment variables %s: rename them to the COMPLIANCEOS_ prefix "
            "(the CELESTIA_ prefix will stop working in a later release)",
            ", ".join(used),
        )
    return used
