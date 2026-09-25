from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user_guides import UserGuide
    from sqlalchemy.ext.asyncio import AsyncSession


async def save_file(
    _db: "AsyncSession",
    record: "UserGuide",
    content: bytes,
) -> None:
    record.file_data = content
    record.storage_backend = "db"
    record.storage_key = None


async def load_file(
    _db: "AsyncSession",
    record: "UserGuide",
) -> bytes:
    if record.file_data is None:
        raise ValueError(f"UserGuide {record.id} has no file_data")
    return bytes(record.file_data)
