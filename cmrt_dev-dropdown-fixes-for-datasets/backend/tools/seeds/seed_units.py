"""
Seed script: units
Inserts standard units of measurement used across the CMRT.
Idempotent — uses INSERT ... ON CONFLICT DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_units
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

UNITS = [
    # (code, label)
    # Mass
    ("kg",      "kg"),
    ("t",       "t"),
    # Length
    ("km",      "km"),
    ("m",       "m"),
    # Area
    ("m2",      "m²"),
    ("ha",      "ha"),
    # Volume
    ("m3",      "m³"),
    ("L",       "L"),
    ("kL",      "kL"),
    ("ML",      "ML"),
    # Electrical energy / power
    ("W",       "W"),
    ("J",       "J"),
    ("Ws",      "Ws"),
    ("Wh",      "Wh"),
    ("kWh",     "kWh"),
    ("MWh",     "MWh"),
    ("GWh",     "GWh"),
    # Thermal energy
    ("kJ",      "kJ"),
    ("MJ",      "MJ"),
    ("GJ",      "GJ"),
    # Derived units used in CSVs
    ("J/s",         "J/s"),
    ("t/item",      "t/item"),
    ("t/each",      "t/each"),
    ("t/m",         "t/m"),
    ("t/tonne",     "t/tonne"),
    ("t/t",         "t/t"),
    ("t/week",      "t/week"),
    ("t/litre",     "t/litre"),
    ("t/m3",        "t/m³"),
    ("t/kL",        "t/kL"),
    ("GJ/kL",       "GJ/kL"),
    # Emissions accounting
    ("tCO2e",           "tCO₂e"),
    ("kgCO2e",          "kgCO₂e"),
    ("gCO2e",           "gCO₂e"),
    ("tCO2e/kWh",       "tCO₂e/kWh"),
    ("kgCO2e/kWh",      "kgCO₂e/kWh"),
    ("kgCO2e/km",       "kgCO₂e/km"),
    ("tCO2e/km",        "tCO₂e/km"),
    ("kgCO2e/L",        "kgCO₂e/L"),
    ("tCO2e/MJ",        "tCO₂e/MJ"),
    ("kgCO2e/MJ",       "kgCO₂e/MJ"),
    ("tCO2e/GJ",        "tCO₂e/GJ"),
    ("kgCO2e/GJ",       "kgCO₂e/GJ"),
    ("gCO2e/km",        "gCO₂e/km"),
    ("kg CO2e",         "kg CO₂e"),
    ("g CO2e",          "g CO₂e"),
    ("kg CO2e/km",      "kg CO₂e/km"),
    ("kgCO2e/t.km",     "kgCO₂e/t·km"),
    ("tCO2e/t.km",      "tCO₂e/t·km"),
    # Rates
    ("MJ/L",    "MJ/L"),
    ("MJ/kg",   "MJ/kg"),
    ("MJ/kWh",  "MJ/kWh"),
    ("MJ/m3",   "MJ/m³"),
    ("GJ/t",    "GJ/t"),
    ("L/100km", "L/100km"),
    ("kWh/km",  "kWh/km"),
    # Generic
    ("%",       "%"),
    ("unit",    "unit"),
    ("no-unit", "no-unit"),
    # Discrete / temporal (Grade 2 benchmarks)
    ("each",            "each"),
    ("week",            "week"),
    ("m2_per_week",     "m²/week"),
    ("each_per_week",   "each/week"),
    # Grade 1 functional units (normalised)
    ("m2_gfa",              "m² GFA"),
    ("lane_km",             "lane·km"),
    ("aud_material_spend",  "AUD material spend"),
    # Grade 3/4 transport and commute units
    ("pkm",     "pkm"),
    ("tkm",     "tkm"),
    ("GTK",     "GTK"),
    # Temporal / other Grade 2–4 units
    ("no",          "no"),
    ("hour",        "hour"),
    ("days",        "days"),
    ("month",       "month"),
    ("each_mix",    "each_mix"),
    # Additional density units
    ("t/bag",       "t/bag"),
    ("t/metre",     "t/metre"),
    ("t/metre_",    "t/metre_"),
    ("t/hour",      "t/hour"),
    ("t/day",       "t/day"),
    ("t/ea",        "t/ea"),
    ("t/no",        "t/no"),
    ("t/unit",      "t/unit"),
    ("t/Unit",      "t/Unit"),
    ("t//m/week",   "t//m/week"),
    ("t/m2",        "t/m²"),
    ("t/kg",        "t/kg"),
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for code, label in UNITS:
            result = await conn.execute(
                text(
                    "INSERT INTO units (id, code, label) VALUES (gen_random_uuid(), :code, :label) "
                    "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label"
                ),
                {"code": code, "label": label},
            )
            inserted += result.rowcount
        print(f"[seed_units] {inserted}/{len(UNITS)} rows upserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
