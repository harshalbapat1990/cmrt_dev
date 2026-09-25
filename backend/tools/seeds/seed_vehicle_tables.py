"""
Seed: vehicle reference tables — CSV-driven.

Reads (from backend/tools/seeds/data/):
  - Vehicle Masses.csv
  - Interrupted Vehicles.csv
  - Uninterrupted Vehicles.csv
  - Vehicle energy conversion rates.csv

Seeding order:
  1. vehicle_classes    — from Vehicle Masses.csv column order, ON CONFLICT DO NOTHING
  2. vehicle_masses     — ON CONFLICT(vehicle_class_id) DO UPDATE SET all fields
  3. interrupted_vehicles
  4. uninterrupted_vehicles  — gradient '-' → 0
  5. vehicle_energy_conversion_rates  — pct '20%' → 0.20

Run from backend/:
    python -m tools.seeds.seed_vehicle_tables
"""
from __future__ import annotations

import asyncio
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings

DATA_DIR = Path(__file__).parent / "data"


def _d(raw: str) -> Optional[Decimal]:
    """Parse a decimal string; return None if empty or unparseable."""
    cleaned = raw.strip().rstrip("%")
    if not cleaned or cleaned in ("\\", "-", "–"):
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _pct(raw: str) -> Decimal:
    """Parse '20%' → Decimal('0.20'); '0.20' → Decimal('0.20')."""
    cleaned = raw.strip()
    if cleaned.endswith("%"):
        val = Decimal(cleaned.rstrip("%"))
        return (val / 100).quantize(Decimal("0.0001"))
    return Decimal(cleaned)


def _gradient(raw: str) -> Decimal:
    """Parse gradient column: '-' or whitespace → 0; else the number."""
    cleaned = raw.strip()
    if not cleaned or set(cleaned) <= {"-", " "}:
        return Decimal("0")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # ── 1. Build vehicle_classes from Vehicle Masses.csv order ──────────
        masses_path = DATA_DIR / "Final Data" / "Vehicle masses.csv"
        with open(masses_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            vehicle_class_names = [row["VehicleClass"].strip() for row in reader if row["VehicleClass"].strip()]

        for sort_order, name in enumerate(vehicle_class_names):
            await session.execute(
                text(
                    "INSERT INTO vehicle_classes (name, sort_order) "
                    "VALUES (:name, :sort_order) "
                    "ON CONFLICT (name) DO UPDATE SET sort_order = EXCLUDED.sort_order"
                ),
                {"name": name, "sort_order": sort_order},
            )

        # Build name→id lookup
        result = await session.execute(text("SELECT id, name FROM vehicle_classes"))
        vc_map: dict[str, str] = {row.name: str(row.id) for row in result}

        print(f"  vehicle_classes: {len(vc_map)} rows")

        # ── 2. vehicle_masses ────────────────────────────────────────────────
        with open(masses_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                name = row["VehicleClass"].strip()
                vc_id = vc_map.get(name)
                if not vc_id:
                    continue
                ref_gcm = _d(row["Reference GCM (tonnes)"])
                max_payload = _d(row["Max Payload (tonnes)"])
                gvm = _d(row["GVM"])
                assumed_pct = Decimal("0.75")  # Fixed at 75% — Assumed Payload removed from new CSV

                await session.execute(
                    text(
                        "INSERT INTO vehicle_masses "
                        "  (vehicle_class_id, reference_gcm_tonnes, max_payload_tonnes, gvm_tonnes, assumed_payload_pct) "
                        "VALUES (:vc_id, :ref_gcm, :max_payload, :gvm, :assumed_pct) "
                        "ON CONFLICT (vehicle_class_id) DO UPDATE SET "
                        "  reference_gcm_tonnes = EXCLUDED.reference_gcm_tonnes, "
                        "  max_payload_tonnes   = EXCLUDED.max_payload_tonnes, "
                        "  gvm_tonnes           = EXCLUDED.gvm_tonnes, "
                        "  assumed_payload_pct  = EXCLUDED.assumed_payload_pct"
                    ),
                    {
                        "vc_id": vc_id,
                        "ref_gcm": ref_gcm,
                        "max_payload": max_payload,
                        "gvm": gvm,
                        "assumed_pct": assumed_pct,
                    },
                )
                count += 1
        print(f"  vehicle_masses: {count} rows upserted")

        # ── 3. interrupted_vehicles ──────────────────────────────────────────
        interrupted_path = DATA_DIR / "Final Data" / "Stop-start.csv"
        with open(interrupted_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                name = row["Vehicle type"].strip()
                vc_id = vc_map.get(name)
                if not vc_id:
                    print(f"    [WARN] interrupted_vehicles: unknown class '{name}', skipping")
                    continue
                coeff_a = _d(row["A"])
                coeff_b = _d(row["B"])
                if coeff_a is None or coeff_b is None:
                    continue
                await session.execute(
                    text(
                        "INSERT INTO interrupted_vehicles (vehicle_class_id, dataset_revision_id, coefficient_a, coefficient_b) "
                        "VALUES (:vc_id, :dataset_revision_id, :a, :b) "
                        "ON CONFLICT (vehicle_class_id) WHERE dataset_revision_id IS NULL DO UPDATE SET "
                        "  coefficient_a = EXCLUDED.coefficient_a, "
                        "  coefficient_b = EXCLUDED.coefficient_b"
                    ),
                    {"vc_id": vc_id, "dataset_revision_id": None, "a": coeff_a, "b": coeff_b},
                )
                count += 1
        print(f"  interrupted_vehicles: {count} rows upserted")

        # ── 4. uninterrupted_vehicles ────────────────────────────────────────
        uninterrupted_path = DATA_DIR / "Final Data" / "Uninterrupted (free flow).csv"
        with open(uninterrupted_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                name = row["Vehicle Class"].strip()
                vc_id = vc_map.get(name)
                if not vc_id:
                    print(f"    [WARN] uninterrupted_vehicles: unknown class '{name}', skipping")
                    continue
                gradient = _gradient(row["Gradient (m/km)"])
                curvature = _d(row["Curvature (deg/km)"])
                base_fuel = _d(row["Base Fuel (L/100km)"])
                k1 = _d(row["K1"])
                k2 = _d(row["K2"])
                k3 = _d(row["K3"])
                k4 = _d(row["K4"])
                k5 = _d(row["K5"])
                if any(v is None for v in [curvature, base_fuel, k1, k2, k3, k4, k5]):
                    continue
                await session.execute(
                    text(
                        "INSERT INTO uninterrupted_vehicles "
                        "  (vehicle_class_id, dataset_revision_id, gradient_m_per_km, curvature_deg_per_km, "
                        "   base_fuel_l_per_100km, k1, k2, k3, k4, k5) "
                        "VALUES (:vc_id, :dataset_revision_id, :grad, :curv, :base_fuel, :k1, :k2, :k3, :k4, :k5) "
                        "ON CONFLICT (vehicle_class_id, gradient_m_per_km, curvature_deg_per_km) WHERE dataset_revision_id IS NULL DO UPDATE SET "
                        "  base_fuel_l_per_100km = EXCLUDED.base_fuel_l_per_100km, "
                        "  k1 = EXCLUDED.k1, k2 = EXCLUDED.k2, k3 = EXCLUDED.k3, "
                        "  k4 = EXCLUDED.k4, k5 = EXCLUDED.k5"
                    ),
                    {
                        "vc_id": vc_id,
                        "dataset_revision_id": None,
                        "grad": gradient,
                        "curv": curvature,
                        "base_fuel": base_fuel,
                        "k1": k1, "k2": k2, "k3": k3, "k4": k4, "k5": k5,
                    },
                )
                count += 1
        print(f"  uninterrupted_vehicles: {count} rows upserted")

        # ── 5. vehicle_energy_conversion_rates ───────────────────────────────
        energy_path = DATA_DIR / "Final Data" / "Vehicle energy conversion rates.csv"
        with open(energy_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                name = row["ATAP vehicle class"].strip()
                vc_id = vc_map.get(name)
                if not vc_id:
                    print(f"    [WARN] vehicle_energy_conversion_rates: unknown class '{name}', skipping")
                    continue
                ev_cat = row["Corresponding EV projection vehicle category"].strip()
                primary_fuel = row["Primary ICE Fuel"].strip()
                hybrid_pct = _pct(row["Hybrid fuel savings (%)"])
                phev_pct = _pct(row["PHEV fuel savings (%)"])
                bev_shift = _d(row["BEV energy shift (kWh/L)"])
                fcev = _d(row["FCEV hydrogen consumption (kWh/L)"])
                source = row.get("Source/Comments", "").strip() or None
                if bev_shift is None or fcev is None:
                    continue
                await session.execute(
                    text(
                        "INSERT INTO vehicle_energy_conversion_rates "
                        "  (vehicle_class_id, dataset_revision_id, ev_projection_category, primary_ice_fuel, "
                        "   hybrid_fuel_savings_pct, phev_fuel_savings_pct, "
                        "   bev_energy_shift_kwh_per_l, fcev_hydrogen_consumption_kwh_per_l, "
                        "   source_comments) "
                        "VALUES (:vc_id, :dataset_revision_id, :ev_cat, :primary_fuel, :hybrid_pct, :phev_pct, "
                        "        :bev_shift, :fcev, :source) "
                        "ON CONFLICT (vehicle_class_id) WHERE dataset_revision_id IS NULL DO UPDATE SET "
                        "  ev_projection_category             = EXCLUDED.ev_projection_category, "
                        "  primary_ice_fuel                   = EXCLUDED.primary_ice_fuel, "
                        "  hybrid_fuel_savings_pct            = EXCLUDED.hybrid_fuel_savings_pct, "
                        "  phev_fuel_savings_pct              = EXCLUDED.phev_fuel_savings_pct, "
                        "  bev_energy_shift_kwh_per_l         = EXCLUDED.bev_energy_shift_kwh_per_l, "
                        "  fcev_hydrogen_consumption_kwh_per_l = EXCLUDED.fcev_hydrogen_consumption_kwh_per_l, "
                        "  source_comments                    = EXCLUDED.source_comments"
                    ),
                    {
                        "vc_id": vc_id,
                        "dataset_revision_id": None,
                        "ev_cat": ev_cat,
                        "primary_fuel": primary_fuel,
                        "hybrid_pct": hybrid_pct,
                        "phev_pct": phev_pct,
                        "bev_shift": bev_shift,
                        "fcev": fcev,
                        "source": source,
                    },
                )
                count += 1
        print(f"  vehicle_energy_conversion_rates: {count} rows upserted")

        await session.commit()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
