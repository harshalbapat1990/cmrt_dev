from __future__ import annotations

from typing import Optional

# Order matters: match longer suffixes first.
_MITIGATION_SUFFIXES = (
    "-mitigation-subst-replaced",
    "-mitigation-subst-adopted",
    "-mitigation",
)


def mitigation_base_table_key(ui_table_key: Optional[str]) -> str:
    """Return the base ui_table_key by stripping known mitigation suffixes."""
    key = ui_table_key or ""
    for suffix in _MITIGATION_SUFFIXES:
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


def matches_base_table_key(ui_table_key: Optional[str], base_key: str) -> bool:
    return mitigation_base_table_key(ui_table_key) == base_key
