"""
Generates a self-contained SQL INSERT script for background_grade_metrics.
No database connection required — all FK lookups are done via subqueries.

Run from the backend/ directory:
    python tools/seeds/generate_background_grade_metrics_sql.py

Output: tools/seeds/background_grade_metrics_seed.sql
Paste that file into Azure Data Studio, pgAdmin, or any SQL editor.
"""
import csv
import uuid
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

DATA_DIR  = Path(__file__).parent / "data"
OUT_FILE  = Path(__file__).parent / "background_grade_metrics_seed.sql"

CSV_GRADE1_CAPEX = "Final Data/Asset Level Benchmarks for CAPEX only.csv"
CSV_GRADE1_FU    = "Final Data/Asset Level Benchmarks for various functional units.csv"
CSV_GRADE2       = "Final Data/Component Level Benchmarks.csv"
CSV_GRADE34      = "Final Data/Grade 3-4 Detailed.csv"

UNIT_MAP: dict[str, str] = {
    "m2  GFA":          "m2_gfa",
    "m2 GFA":           "m2_gfa",
    "lane km":          "lane_km",
    "$ material spend": "aud_material_spend",
    "m2/week":          "m2_per_week",
    "each/week":        "each_per_week",
    "m2":   "m2",
    "m3":   "m3",
    "m":    "m",
    "t":    "t",
    "kL":   "kL",
    "each": "each",
    "Each": "each",
    "week": "week",
    "%":    "%",
    "pkm":      "pkm",
    "tkm":      "tkm",
    "GTK":      "GTK",
    "no":       "no",
    "No":       "no",
    "hour":     "hour",
    "days":     "days",
    "month":    "month",
    "each mix": "each_mix",
    "MWh":  "MWh",
    "kWh":  "kWh",
    "GJ":   "GJ",
    "km":   "km",
    "L":    "L",
}

VALUE_BANDS = ("Low", "Mid", "High")

# Characters in the CSV that must be normalised before DB lookups or SQL literals.
# The seeds store names with ASCII/straight quotes; the CSVs use Unicode variants.
_UNICODE_NORMALISE = str.maketrans({
    "\u2019": "'",   # RIGHT SINGLE QUOTATION MARK → straight apostrophe
    "\u2018": "'",   # LEFT  SINGLE QUOTATION MARK → straight apostrophe
    "\u201c": '"',   # LEFT  DOUBLE QUOTATION MARK → straight double quote
    "\u201d": '"',   # RIGHT DOUBLE QUOTATION MARK → straight double quote
    "\u2011": "-",   # NON-BREAKING HYPHEN         → hyphen-minus
    "\u2013": "-",   # EN DASH                     → hyphen-minus
    "\u2014": "-",   # EM DASH                     → hyphen-minus
    "\u00a0": " ",   # NO-BREAK SPACE              → regular space
})


def _norm(s: str | None) -> str | None:
    """Normalise Unicode punctuation variants to ASCII equivalents."""
    if s is None:
        return None
    return s.translate(_UNICODE_NORMALISE)


def _q(v) -> str:
    """Return a SQL-safe literal: NULL, number, or single-quoted string."""
    if v is None:
        return "NULL"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    # Normalise Unicode punctuation then escape single quotes
    s = _norm(str(v))
    return "'" + s.replace("'", "''") + "'"


def _juris_subq(name: str) -> str:
    return f"(SELECT id FROM jurisdictions WHERE name = {_q(name)} LIMIT 1)"


def _factor_set_subq(name: str) -> str:
    return (
        f"(SELECT fs.id FROM emissions_factor_sets fs "
        f"JOIN jurisdictions j ON j.id = fs.jurisdiction_id "
        f"WHERE j.name = {_q(name)} LIMIT 1)"
    )


def _mastertype_subq(name: str) -> str:
    """Subquery for mastertype_id using case-insensitive name match."""
    return f"(SELECT id FROM benchmark_mastertypes WHERE LOWER(name) = LOWER({_q(name)}) LIMIT 1)"


def _typecast_subq(name: str, mastertype_name: str) -> str:
    """Subquery for typecast_id using case-insensitive name match within the given mastertype."""
    return (
        f"(SELECT bt.id FROM benchmark_typecasts bt "
        f"JOIN benchmark_mastertypes bm ON bm.id = bt.mastertype_id "
        f"WHERE LOWER(bt.name) = LOWER({_q(name)}) "
        f"AND LOWER(bm.name) = LOWER({_q(mastertype_name)}) LIMIT 1)"
    )


def _mt_subq(code) -> str:
    if code is None:
        return "NULL"
    return f"(SELECT id FROM metric_types WHERE code = {_q(code)} LIMIT 1)"


def _unit_subq(csv_unit: str) -> str:
    code = UNIT_MAP.get(csv_unit.strip(), csv_unit.strip())
    if not code:
        return "NULL"
    return f"(SELECT id FROM units WHERE code = {_q(code)} LIMIT 1)"


def _ec_subq(name: str | None) -> str:
    """Subquery for emissions_category_id: top-level category lookup by name."""
    if not name:
        return "NULL"
    return f"(SELECT id FROM emissions_categories WHERE name = {_q(name)} AND parent_category_id IS NULL LIMIT 1)"


def _esc_subq(name: str | None, parent_name: str | None) -> str:
    """Subquery for emissions_subcategory_id: child category lookup by name under parent."""
    if not name:
        return "NULL"
    return (
        f"(SELECT id FROM emissions_categories WHERE name = {_q(name)} "
        f"AND parent_category_id = "
        f"(SELECT id FROM emissions_categories WHERE name = {_q(parent_name)} "
        f"AND parent_category_id IS NULL LIMIT 1) LIMIT 1)"
    )


# ---------------------------------------------------------------------------
# Grade 3 & 4 specific subqueries
#
# Several top-level category names used in the grade 3/4 CSV (e.g. "Materials",
# "Waste", "Water", "Fuels") also exist in the general CMRT emissions category
# tree (0001 / 0003 series UUIDs).  A plain LIMIT 1 can resolve to the wrong
# parent because PostgreSQL does not guarantee result order without ORDER BY.
#
# The grade-3/4 dedicated categories live in the 0007 series
# (id LIKE '00000000-0007-%'), so we filter on that UUID prefix to ensure we
# always land in the right parent when building INSERT sub-queries.
# ---------------------------------------------------------------------------

def _ec_subq_g34(name: str | None) -> str:
    """Top-level category lookup restricted to the Grade 3/4 (0007-series) tree."""
    if not name:
        return "NULL"
    return (
        f"(SELECT id FROM emissions_categories "
        f"WHERE name = {_q(name)} "
        f"AND parent_category_id IS NULL "
        f"AND id::text LIKE '00000000-0007-%' "
        f"LIMIT 1)"
    )


def _esc_subq_g34(name: str | None, parent_name: str | None) -> str:
    """Sub-category lookup restricted to the Grade 3/4 (0007/0008-series) tree."""
    if not name:
        return "NULL"
    return (
        f"(SELECT id FROM emissions_categories "
        f"WHERE name = {_q(name)} "
        f"AND parent_category_id = ("
        f"SELECT id FROM emissions_categories "
        f"WHERE name = {_q(parent_name)} "
        f"AND parent_category_id IS NULL "
        f"AND id::text LIKE '00000000-0007-%' "
        f"LIMIT 1) "
        f"LIMIT 1)"
    )


def _parse_value(raw: str):
    v = raw.strip().rstrip("%").strip()
    if not v or set(v) <= {"-", " "}:
        return None
    # Strip thousands-separator commas (e.g. "12,400.00" → "12400.00")
    v = v.replace(",", "")
    try:
        return float(Decimal(v))
    except InvalidOperation:
        return None


def _insert(row_dict: dict) -> str:
    """Render one INSERT statement for a single row."""
    r = row_dict
    cols = (
        "id, factor_set_id, grade_id, jurisdiction_id, "
        "mastertype_id, typecast_id, "
        "emissions_category_id, emissions_subcategory_id, emissions_source, "
        "lifecycle_module_code, ghg_scope_id, metric_type_id, "
        "band_code, unit_id, value, assumed_quantity_default, source"
    )
    vals = ", ".join([
        _q(str(uuid.uuid4())),          # id
        r["factor_set_subq"],           # factor_set_id  (subquery, no quotes)
        str(r["grade_id"]),             # grade_id
        r["jurisdiction_subq"],         # jurisdiction_id (subquery)
        r.get("mastertype_subq", "NULL"),   # mastertype_id (subquery or NULL)
        r.get("typecast_subq", "NULL"),     # typecast_id (subquery or NULL)
        r["emissions_category_id_subq"],    # emissions_category_id (subquery, no quotes)
        r["emissions_subcategory_id_subq"], # emissions_subcategory_id (subquery, no quotes)
        _q(r["emissions_source"]),
        _q(r["lifecycle_module_code"]),
        _q(r["ghg_scope_id"]),
        r["metric_type_subq"],          # metric_type_id (subquery)
        _q(r["band_code"]),
        r["unit_subq"],                 # unit_id (subquery)
        _q(r["value"]),
        _q(r["assumed_quantity_default"]),
        _q(r["source"]),
    ])
    return f"INSERT INTO background_grade_metrics ({cols}) VALUES ({vals});"


def gen_grade1_capex() -> list[str]:
    metric_cols = [
        ("Material share of CAPEX",                                            "material_share_capex",    None,    "%"),
        ("Product stage (A1-A3) Emission intensity (tCO2e/$ material spend)", "emission_intensity_a1_a3", "A1-A3", "$ material spend"),
        ("transport (A4) Emission intensity (tCO2e/$ material spend)",         "emission_intensity_a4",    "A4",    "$ material spend"),
        ("Construction (A5) Emission intensity (tCO2e/$ material spend)",      "emission_intensity_a5",    "A5",    "$ material spend"),
    ]
    SOURCE_TAG = "Grade 1 CAPEX Benchmarks (AU)"
    stmts: list[str] = []
    rows_by_j: dict[str, list] = defaultdict(list)
    with open(DATA_DIR / CSV_GRADE1_CAPEX, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows_by_j[row["Jurisdiction"].strip()].append(row)

    for jname, jrows in rows_by_j.items():
        fs_subq = _factor_set_subq(jname)
        ju_subq = _juris_subq(jname)
        for row in jrows:
            mastertype_name = row.get("Mastertype", "").strip() or None
            typecast_name   = row.get("Typecast", "").strip() or None
            mt_subq = _mastertype_subq(mastertype_name) if mastertype_name else "NULL"
            tc_subq = _typecast_subq(typecast_name, mastertype_name) if (typecast_name and mastertype_name) else "NULL"
            for col_prefix, mt_code, lifecycle, unit_key in metric_cols:
                for band in VALUE_BANDS:
                    value = _parse_value(row.get(f"{col_prefix} - {band}", ""))
                    stmts.append(_insert({
                        "factor_set_subq":    fs_subq,
                        "grade_id":           1,
                        "jurisdiction_subq":  ju_subq,
                        "mastertype_subq":    mt_subq,
                        "typecast_subq":      tc_subq,
                        "emissions_category_id_subq":    "NULL",
                        "emissions_subcategory_id_subq": "NULL",
                        "emissions_source":   None,
                        "lifecycle_module_code": lifecycle,
                        "ghg_scope_id":       None,
                        "metric_type_subq":   _mt_subq(mt_code),
                        "band_code":          band,
                        "unit_subq":          _unit_subq(unit_key),
                        "value":              value,
                        "assumed_quantity_default": None,
                        "source":             SOURCE_TAG,
                    }))
    return stmts


def gen_grade1_fu() -> list[str]:
    metric_cols = [
        ("Product stage (A1-A3) Emission intensity  (tCO2e/unit)", "emission_intensity_a1_a3", "A1-A3"),
        ("Transport (A4) Emission intensity (tCO2e/unit)",         "emission_intensity_a4",    "A4"),
        ("Construction (A5) Emission intensity (tCO2e/unit)",      "emission_intensity_a5",    "A5"),
    ]
    SOURCE_TAG = "Grade 1 FU Benchmarks"
    stmts: list[str] = []
    rows_by_j: dict[str, list] = defaultdict(list)
    with open(DATA_DIR / CSV_GRADE1_FU, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows_by_j[row["Jurisdiction"].strip()].append(row)

    for jname, jrows in rows_by_j.items():
        fs_subq = _factor_set_subq(jname)
        ju_subq = _juris_subq(jname)
        for row in jrows:
            unit_subq = _unit_subq(row.get("Functional unit", "").strip())
            mastertype_name = row.get("Mastertype", "").strip() or None
            typecast_name   = row.get("Typecast", "").strip() or None
            mt_subq = _mastertype_subq(mastertype_name) if mastertype_name else "NULL"
            tc_subq = _typecast_subq(typecast_name, mastertype_name) if (typecast_name and mastertype_name) else "NULL"
            for col_prefix, mt_code, lifecycle in metric_cols:
                for band in VALUE_BANDS:
                    value = _parse_value(row.get(f"{col_prefix} - {band}", ""))
                    stmts.append(_insert({
                        "factor_set_subq":    fs_subq,
                        "grade_id":           1,
                        "jurisdiction_subq":  ju_subq,
                        "mastertype_subq":    mt_subq,
                        "typecast_subq":      tc_subq,
                        "emissions_category_id_subq":    "NULL",
                        "emissions_subcategory_id_subq": "NULL",
                        "emissions_source":   None,
                        "lifecycle_module_code": lifecycle,
                        "ghg_scope_id":       None,
                        "metric_type_subq":   _mt_subq(mt_code),
                        "band_code":          band,
                        "unit_subq":          unit_subq,
                        "value":              value,
                        "assumed_quantity_default": None,
                        "source":             SOURCE_TAG,
                    }))
    return stmts


def gen_grade2() -> list[str]:
    value_cols = [
        ("Carbon Storage (tCO2e/UoM)",                           "carbon_storage",           None),
        ("Product Stage (A1-3) Emissions Factor (tCO2e/UoM)",    "emission_intensity_a1_a3", "A1-A3"),
        ("Transport Stage (A4) Emissions Factor (tCO2e/UoM)",    "emission_intensity_a4",    "A4"),
        ("Construction Stage (A5) Emissions Factor (tCO2e/UoM)", "emission_intensity_a5",    "A5"),
    ]
    stmts: list[str] = []
    rows_by_j: dict[str, list] = defaultdict(list)
    with open(DATA_DIR / CSV_GRADE2, newline="", encoding="cp1252") as f:
        for row in csv.DictReader(f):
            if not any(row.values()):
                continue
            jname = row.get("Jurisdiction", "").strip()
            if jname:
                rows_by_j[jname].append(row)

    for jname, jrows in rows_by_j.items():
        fs_subq = _factor_set_subq(jname)
        ju_subq = _juris_subq(jname)
        for row in jrows:
            unit_subq = _unit_subq(row.get("UoM", "").strip())
            assumed   = _parse_value(row.get("Quantity", ""))
            source    = row.get("Source/Comments", row.get("Source", "")).strip() or None
            ec_name   = row.get("Emissions Category", "").strip() or None
            esc_name  = row.get("Emissions Sub-Category", "").strip() or None
            for col, mt_code, lifecycle in value_cols:
                value = _parse_value(row.get(col, ""))
                if value is None:
                    continue
                stmts.append(_insert({
                    "factor_set_subq":               fs_subq,
                    "grade_id":                      2,
                    "jurisdiction_subq":             ju_subq,
                    "emissions_category_id_subq":    _ec_subq(ec_name),
                    "emissions_subcategory_id_subq": _esc_subq(esc_name, ec_name),
                    "emissions_source":              row.get("Emissions Source", "").strip() or None,
                    "lifecycle_module_code":         lifecycle,
                    "ghg_scope_id":                  None,
                    "metric_type_subq":              _mt_subq(mt_code),
                    "band_code":                     None,
                    "unit_subq":                     unit_subq,
                    "value":                         value,
                    "assumed_quantity_default":      assumed,
                    "source":                        source,
                }))
    return stmts


def gen_grade34() -> list[str]:
    value_cols = [
        ("Carbon Storage (tCO2e/UoM)",           "carbon_storage",        None, None),
        ("Scope 1 Emissions Factor (tCO2e/UoM)", "emission_factor_scope1", None, 1),
        ("Scope 3 Emissions Factor (tCO2e/UoM)", "emission_factor_scope3", None, 3),
    ]
    stmts: list[str] = []
    rows_by_j: dict[str, list] = defaultdict(list)
    with open(DATA_DIR / CSV_GRADE34, newline="", encoding="cp1252") as f:
        for row in csv.DictReader(f):
            if not any(row.values()):
                continue
            jname = row.get("Jurisdiction", "").strip()
            if jname:
                rows_by_j[jname].append(row)

    for jname, jrows in rows_by_j.items():
        fs_subq = _factor_set_subq(jname)
        ju_subq = _juris_subq(jname)
        for grade_id in (3, 4):
            for row in jrows:
                unit_subq = _unit_subq(row.get("UoM", "").strip())
                source    = row.get("Source/Comments", row.get("Source", "")).strip() or None
                ec_name   = row.get("Emissions Category", "").strip() or None
                esc_name  = row.get("Emissions Sub-Category", "").strip() or None
                for col, mt_code, lifecycle, ghg_scope in value_cols:
                    value = _parse_value(row.get(col, ""))
                    if value is None:
                        continue
                    stmts.append(_insert({
                        "factor_set_subq":               fs_subq,
                        "grade_id":                      grade_id,
                        "jurisdiction_subq":             ju_subq,
                        # Use grade-34-specific subqueries to target the 0007/0008 UUID series,
                        # avoiding false matches against the 0001/0003 series which share some
                        # top-level category names (Materials, Waste, Water, Fuels, etc.).
                        "emissions_category_id_subq":    _ec_subq_g34(ec_name),
                        "emissions_subcategory_id_subq": _esc_subq_g34(esc_name, ec_name),
                        "emissions_source":              row.get("Emissions Source", "").strip() or None,
                        "lifecycle_module_code":         lifecycle,
                        "ghg_scope_id":                  ghg_scope,
                        "metric_type_subq":              _mt_subq(mt_code),
                        "band_code":                     None,
                        "unit_subq":                     unit_subq,
                        "value":                         value,
                        "assumed_quantity_default":      None,
                        "source":                        source,
                    }))
    return stmts


def main():
    print("Generating SQL...")
    all_stmts: list[str] = []

    g1c = gen_grade1_capex()
    print(f"  Grade 1 CAPEX:  {len(g1c)} rows")
    all_stmts += g1c

    g1f = gen_grade1_fu()
    print(f"  Grade 1 FU:     {len(g1f)} rows")
    all_stmts += g1f

    g2 = gen_grade2()
    print(f"  Grade 2:        {len(g2)} rows")
    all_stmts += g2

    g34 = gen_grade34()
    print(f"  Grades 3 & 4:   {len(g34)} rows")
    all_stmts += g34

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("-- background_grade_metrics seed\n")
        f.write("-- Generated by generate_background_grade_metrics_sql.py\n")
        f.write(f"-- Total rows: {len(all_stmts)}\n\n")
        f.write("BEGIN;\n\n")
        for stmt in all_stmts:
            f.write(stmt + "\n")
        f.write("\nCOMMIT;\n")

    print(f"\nDone. Written to: {OUT_FILE}")
    print(f"Total INSERT statements: {len(all_stmts)}")

    replace_file_g2 = Path(__file__).parent / "background_grade_metrics_grade2_replace.sql"
    with open(replace_file_g2, "w", encoding="utf-8") as f:
        f.write("-- Grade 2 background_grade_metrics REPLACEMENT script\n")
        f.write("-- Generated by generate_background_grade_metrics_sql.py\n")
        f.write(f"-- CSV source: {CSV_GRADE2}\n")
        f.write(f"-- Grade 2 INSERT rows: {len(g2)}\n\n")
        f.write("BEGIN;\n\n")
        f.write("-- 1. Remove dependent rows that reference grade 2 metrics\n")
        f.write("DELETE FROM dataset_revision_changes\n")
        f.write("  WHERE metric_id IN (SELECT id FROM background_grade_metrics WHERE grade_id = 2);\n\n")
        f.write("DELETE FROM project_dataset_exclusions\n")
        f.write("  WHERE metric_id IN (SELECT id FROM background_grade_metrics WHERE grade_id = 2);\n\n")
        f.write("UPDATE activity_data\n")
        f.write("  SET metric_id = NULL\n")
        f.write("  WHERE metric_id IN (SELECT id FROM background_grade_metrics WHERE grade_id = 2);\n\n")
        f.write("-- 2. Delete old grade 2 rows\n")
        f.write("DELETE FROM background_grade_metrics WHERE grade_id = 2;\n\n")
        f.write("-- 3. Insert fresh grade 2 rows from v3 CSV\n")
        for stmt in g2:
            f.write(stmt + "\n")
        f.write("\nCOMMIT;\n")
    print(f"  Grade 2 replace script: {replace_file_g2}")

    # Use this when grades 1 & 2 are already in the DB and only grade 3 & 4 need replacing.
    replace_file = Path(__file__).parent / "background_grade_metrics_grade34_replace.sql"
    with open(replace_file, "w", encoding="utf-8") as f:
        f.write("-- Grade 3 & 4 background_grade_metrics REPLACEMENT script\n")
        f.write("-- Generated by generate_background_grade_metrics_sql.py\n")
        f.write(f"-- CSV source: {CSV_GRADE34}\n")
        f.write(f"-- Grade 3 & 4 INSERT rows: {len(g34)}\n\n")
        f.write("BEGIN;\n\n")
        f.write("-- 1. Remove dependent rows that reference grade 3 & 4 metrics\n")
        f.write("DELETE FROM dataset_revision_changes\n")
        f.write("  WHERE metric_id IN (SELECT id FROM background_grade_metrics WHERE grade_id IN (3, 4));\n\n")
        f.write("DELETE FROM project_dataset_exclusions\n")
        f.write("  WHERE metric_id IN (SELECT id FROM background_grade_metrics WHERE grade_id IN (3, 4));\n\n")
        f.write("UPDATE activity_data\n")
        f.write("  SET metric_id = NULL\n")
        f.write("  WHERE metric_id IN (SELECT id FROM background_grade_metrics WHERE grade_id IN (3, 4));\n\n")
        f.write("-- 2. Delete old grade 3 & 4 rows\n")
        f.write("DELETE FROM background_grade_metrics WHERE grade_id IN (3, 4);\n\n")
        f.write("-- 3. Insert new grade 3 & 4 rows from v2 CSV\n")
        for stmt in g34:
            f.write(stmt + "\n")
        f.write("\nCOMMIT;\n")

    print(f"\nGrade 3 & 4 replacement script written to: {replace_file}")


if __name__ == "__main__":
    main()
