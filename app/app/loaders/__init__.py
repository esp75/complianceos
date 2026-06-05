"""Framework loaders.

Transform Celestia ``openlane.io/v1`` Framework/Control YAML (under
``layers/L1-substrate/frameworks/``) into theopenlane GraphQL
createStandard / createControl / createSubcontrol mutations. theopenlane has no
native framework-YAML import (ADR-0012), so this is the ingestion path.
"""
