"""
crud/audit_logs.py
==================
Helpers for writing and querying audit log entries.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.audit_logs import AuditLog


async def write_audit_event(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    performed_by: Optional[uuid.UUID] = None,
    performed_by_org: Optional[uuid.UUID] = None,
    performed_by_email: Optional[str] = None,
    performed_by_org_name: Optional[str] = None,
    entity_name: Optional[str] = None,
    field_name: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Write a single audit log row and flush to the session (not committed).
    """
    from core.audit_context import get_audit_actor
    ctx = get_audit_actor()
    if ctx is not None:
        if performed_by is None:
            performed_by = ctx.user_id
        if performed_by_org is None:
            performed_by_org = ctx.org_id
        if performed_by_email is None:
            performed_by_email = ctx.display_name
        if performed_by_org_name is None:
            performed_by_org_name = ctx.org_name

    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        performed_by_org=performed_by_org,
        performed_by_email=performed_by_email,
        performed_by_org_name=performed_by_org_name,
        entity_name=entity_name,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        event_metadata=metadata,
    )
    db.add(log)
    await db.flush()
    return log


async def list_audit_logs(
    db: AsyncSession,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    performed_by: Optional[uuid.UUID] = None,
    performed_by_org: Optional[uuid.UUID] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[AuditLog]:
    """Return audit log rows, most-recent first, with optional scoping filters."""
    q = select(AuditLog).order_by(AuditLog.performed_at.desc())
    if entity_type is not None:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.where(AuditLog.entity_id == entity_id)
    if action is not None:
        q = q.where(AuditLog.action == action)
    if performed_by is not None:
        q = q.where(AuditLog.performed_by == performed_by)
    if performed_by_org is not None:
        q = q.where(AuditLog.performed_by_org == performed_by_org)
    if from_date is not None:
        q = q.where(AuditLog.performed_at >= from_date)
    if to_date is not None:
        q = q.where(AuditLog.performed_at <= to_date)
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()

