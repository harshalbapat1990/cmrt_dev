"""Install the revision-aware Australian vehicle-emissions SQL function."""

from pathlib import Path
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)
_FUNCTION_SQL = Path(__file__).resolve().parent.parent / "sql" / "fn_veh_emissions_intensity_aus.sql"
_FUNCTION_SIGNATURE = (
    "public.fn_veh_emissions_intensity_aus(" 
    "integer,text,text,numeric,numeric,numeric,numeric,uuid)"
)


async def ensure_aus_road_emissions_function(engine: AsyncEngine) -> None:
    """Create or refresh the SQL function during API startup.

    `CREATE OR REPLACE` also upgrades older installations that have the legacy
    seven-argument function. The existing overload remains available to other
    callers, while the backend uses the revision-aware eight-argument form.
    """
    function_sql = _FUNCTION_SQL.read_text(encoding="utf-8-sig")
    async with engine.begin() as conn:
        exists = await conn.execute(
            text("SELECT to_regprocedure(:signature) IS NOT NULL"),
            {"signature": _FUNCTION_SIGNATURE},
        )
        was_present = bool(exists.scalar())
        await conn.exec_driver_sql(function_sql)
    logger.info(
        "[bootstrap] Australian road emissions function: %s",
        "updated" if was_present else "created",
    )
