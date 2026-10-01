"""Dentiva Pro — premium offline dental clinic management.

The application is a single-process, offline-first Windows desktop product. Nothing in the
package requires network access, a cloud service or a paid API.
"""

from __future__ import annotations

from dentivapro.version import APP_NAME, CREATOR_EMAIL, CREATOR_NAME, __version__

__all__ = ["APP_NAME", "CREATOR_EMAIL", "CREATOR_NAME", "__version__"]
