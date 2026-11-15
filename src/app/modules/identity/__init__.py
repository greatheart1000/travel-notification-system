"""Identity, tenant and verification domain.

Import concrete modules directly (``app.modules.identity.service`` etc.) so that
``app.modules.integration.auth`` can depend on the repositories without creating
a package-level import cycle.
"""
