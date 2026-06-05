"""Celestia authorization layer.

Realizes the 4-role tetrad (operator / insurer / regulator / admin) on top of
theopenlane's embedded OpenFGA model via Groups + tuples (ADR-0012), without
patching the upstream model. See ``seed_tetrad`` and ``cross-cutting/auth/``.
"""
