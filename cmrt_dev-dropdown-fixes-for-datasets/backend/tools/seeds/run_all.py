"""
Orchestrator: runs all seed scripts in dependency order.

Run from the backend/ directory:
    python -m tools.seeds.run_all
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── RBAC (roles / permissions / mappings) ────────────────────────────────────
from tools.seeds.seed_roles import seed as seed_roles
from tools.seeds.seed_permissions import seed as seed_permissions
from tools.seeds.seed_role_permissions import seed as seed_role_permissions

# ── Demo org + allowed domains (exercises domain-match rule) ─────────────────
from tools.seeds.seed_demo_org import seed as seed_demo_org

# ── Industry organisations (design consultants & construction contractors) ────
from tools.seeds.seed_organizations import seed as seed_organizations

# ── Core reference tables ─────────────────────────────────────────────────────
from tools.seeds.seed_ghg_scopes import seed as seed_ghg_scopes
from tools.seeds.seed_units import seed as seed_units
from tools.seeds.seed_unit_conversions import seed as seed_unit_conversions
from tools.seeds.seed_emissions_categories import seed as seed_emissions_categories
from tools.seeds.seed_lifecycle_modules import seed as seed_lifecycle_modules

# ── Jurisdictions & staging model ─────────────────────────────────────────────
from tools.seeds.seed_jurisdictions import seed as seed_jurisdictions
from tools.seeds.seed_anz_reporting_stages import seed as seed_anz_reporting_stages
from tools.seeds.seed_jurisdiction_reporting_stages import seed as seed_jurisdiction_reporting_stages

# ── Direct substitutions & electricity/recycling assumptions ──────────────────
from tools.seeds.seed_direct_substitutions import seed as seed_direct_substitutions
from tools.seeds.seed_electricity_recycling_assumptions import seed as seed_electricity_recycling_assumptions

# ── Defaults & materials ──────────────────────────────────────────────────────
from tools.seeds.seed_materials import seed as seed_materials
from tools.seeds.seed_waste_treatments import seed as seed_waste_treatments
from tools.seeds.seed_material_recycled_content import seed as seed_material_recycled_content
from tools.seeds.seed_densities import seed as seed_densities
from tools.seeds.seed_default_transport_distances import seed as seed_default_transport_distances
from tools.seeds.seed_default_waste_rates import seed as seed_default_waste_rates
from tools.seeds.seed_base_case_assumptions import seed as seed_base_case_assumptions

# ── Package G — Unified Grade Metrics reference data ─────────────────────────
from tools.seeds.seed_grade_definitions import seed as seed_grade_definitions
from tools.seeds.seed_value_bands import seed as seed_value_bands
from tools.seeds.seed_metric_types import seed as seed_metric_types

# ── Package F — Dataset Revisions ───────────────────────────────────────────────────
from tools.seeds.seed_dataset_revisions import seed as seed_dataset_revisions
# seed_emissions_factor_sets is intentionally excluded — the emissions_factor_sets table
# was dropped in migration 9a8b7c6d5e4f (no-factor-sets delta architecture).

# ── Package G — Background Grade Metrics (CSV import) ────────────────────────
# from tools.seeds.seed_background_grade_metrics import seed as seed_background_grade_metrics
# NOTE: this is deleted as the azure connection to db doesnt stay open and seeding becomes a manual process. The seed script is left in place for local development and testing, but is not run in the run_all orchestrator. Instead we have a sql script that performs a bulk insert from the CSV file directly into the database, which can be run manually as needed.

# ── Application-managed (no-ops) ─────────────────────────────────────────────
from tools.seeds.seed_project_dataset_revisions import seed as seed_project_dataset_revisions
from tools.seeds.seed_dataset_revision_changes import seed as seed_dataset_revision_changes
from tools.seeds.seed_project_dataset_exclusions import seed as seed_project_dataset_exclusions


async def run_all() -> None:
    print("=" * 60)
    print("Running all seed scripts")
    print("=" * 60)

    # Step 0: RBAC — roles, permissions, mappings (no FK deps on ref tables)
    await seed_roles()
    await seed_permissions()
    await seed_role_permissions()

    # Step 0b: Demo org + allowed domains (depends only on organizations table)
    await seed_demo_org()

    # Step 0c: Industry organisations (design consultants & construction contractors)
    await seed_organizations()

    # Step 1: leaf reference tables with no dependencies
    await seed_ghg_scopes()
    await seed_units()
    await seed_unit_conversions()
    await seed_emissions_categories()
    await seed_lifecycle_modules()

    # Step 2: jurisdictions & staging model
    await seed_jurisdictions()
    await seed_anz_reporting_stages()
    await seed_jurisdiction_reporting_stages()

    # Step 2b: jurisdiction-dependent reference data
    await seed_direct_substitutions()
    await seed_electricity_recycling_assumptions()

    # Step 3: defaults & materials
    await seed_materials()
    await seed_waste_treatments()
    await seed_material_recycled_content()
    await seed_densities()
    await seed_default_transport_distances()
    await seed_default_waste_rates()
    await seed_base_case_assumptions()

    # Step 4: grade benchmark reference rows (no FK deps beyond core tables)
    await seed_grade_definitions()
    await seed_value_bands()
    await seed_metric_types()

    # Step 5: dataset revision (depend on jurisdictions)
    await seed_dataset_revisions()
    # seed_emissions_factor_sets skipped — table was dropped in migration 9a8b7c6d5e4f

    # Step 6: CSV import — depends on all of the above
    # await seed_background_grade_metrics()
    # NOTE: Proceed with step 6 after you have successfully run the bulk insert SQL script to load the background_grade_metrics from the CSV file, as this is no longer automated via the seed script due to connection issues with Azure. The seed script is left in place for local development and testing purposes, but is not run in this orchestrator.
    # Step 7: no-ops (application-managed tables)
    await seed_project_dataset_revisions()
    await seed_dataset_revision_changes()
    await seed_project_dataset_exclusions()

    print("=" * 60)
    print("All seed scripts completed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all())
