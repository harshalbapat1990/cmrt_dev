from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass
class AuditActorContext:
    user_id: uuid.UUID
    display_name: str
    org_id: Optional[uuid.UUID] = None
    org_name: Optional[str] = None


_audit_ctx: ContextVar[Optional[AuditActorContext]] = ContextVar(
    "audit_ctx", default=None
)

def set_audit_actor(actor: AuditActorContext) -> None:
    _audit_ctx.set(actor)


def get_audit_actor() -> Optional[AuditActorContext]:
    return _audit_ctx.get()
