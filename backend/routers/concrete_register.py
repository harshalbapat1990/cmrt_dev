from fastapi import APIRouter

# Concrete mix CRUD endpoints were removed in migration dr01_drop_concrete_mix_tables.
# Data is now stored in activity_data (ui_table_key = 'concreteRegSimplified' |
# 'concreteRegDetailed'). Use the /api/activity-data endpoints instead.
# Calculation endpoints remain in concrete_mix_register_calculations.py.

router = APIRouter(prefix="/api/concrete-register", tags=["concrete-register"])
