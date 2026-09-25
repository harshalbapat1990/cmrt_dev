from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.stage_approval_events import StageApprovalEvent


async def record_event(
    db: AsyncSession,
    stage_instance_id: UUID,
    project_id: UUID,
    event_type: str,
    performed_by: Optional[UUID],
    from_status: Optional[str],
    to_status: Optional[str],
    justification: Optional[str] = None,
    report_number: Optional[int] = None,
    submission_period_id: Optional[UUID] = None,
) -> StageApprovalEvent:
    event = StageApprovalEvent(
        stage_instance_id=stage_instance_id,
        project_id=project_id,
        event_type=event_type,
        performed_by=performed_by,
        performed_at=datetime.utcnow(),
        justification=justification,
        from_status=from_status,
        to_status=to_status,
        report_number=report_number,
        submission_period_id=submission_period_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def list_events_for_stage(
    db: AsyncSession,
    stage_instance_id: UUID,
) -> List[StageApprovalEvent]:
    query = (
        select(StageApprovalEvent)
        .where(StageApprovalEvent.stage_instance_id == stage_instance_id)
        .order_by(StageApprovalEvent.performed_at.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()
