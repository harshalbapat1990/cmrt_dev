from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


def _to_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def compute_field_diffs(
    before: Dict[str, Any],
    after: Dict[str, Any],
    exclude_fields: Optional[Set[str]] = None,
) -> List[Dict[str, Optional[str]]]:

    _exclude = (exclude_fields or set()) | {"updated_on", "created_on"}
    diffs: List[Dict[str, Optional[str]]] = []
    all_keys = set(before) | set(after)
    for key in sorted(all_keys):
        if key in _exclude:
            continue
        old_str = _to_str(before.get(key))
        new_str = _to_str(after.get(key))
        if old_str != new_str:
            diffs.append({"field": key, "old_value": old_str, "new_value": new_str})
    return diffs


def orm_to_audit_dict(obj: Any, fields: List[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for f in fields:
        result[f] = getattr(obj, f, None)
    return result
