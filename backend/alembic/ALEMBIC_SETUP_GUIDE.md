# Alembic Migration Setup Guide

## Overview
Alembic is now configured for your FastAPI + SQLAlchemy project. It allows you to:
- Automatically generate migrations when you update your database models
- Track schema changes in version control
- Apply migrations to your database with a single command

## Current Status ✅
- ✅ Alembic initialized
- ✅ Configuration complete (alembic.ini and alembic/env.py)
- ✅ All models imported and configured
- ✅ Initial migration created from existing database
- ✅ Database marked as up-to-date

---

## How to Use

### 1. **Update Your SQLAlchemy Models**
Modify any model in `models/` directory. For example:

```python
# models/users.py
class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    # ADD A NEW FIELD
    phone_number = Column(String(20), nullable=True)  # NEW
```

### 2. **Generate Migration**
After updating models, run:
```bash
cd backend
alembic revision --autogenerate -m "Add phone_number to users"
```

This creates a new migration file in `alembic/versions/` that captures the changes.

### 3. **Review Migration**
Always review the generated migration before applying:
```bash
# Open the latest file in alembic/versions/
# Check that the changes look correct
```

### 4. **Apply Migration**
Apply the migration to your database:
```bash
alembic upgrade head
```

This updates your database schema to match your models.

### 5. **Commit to Version Control**
```bash
git add alembic/versions/
git commit -m "Add migration: Add phone_number to users"
```

---

## Important Commands

### Generate Migration
```bash
cd alembic
alembic revision --autogenerate -m "Description of changes"
```

### Apply Latest Migration
```bash
cd alembic
alembic upgrade head
```

### Rollback Last Migration
```bash
cd alembic
alembic downgrade -1
```

### View Migration History
```bash
cd alembic
alembic history
```

### Check Current Database Version
```bash
cd alembic
alembic current
```

**Note:** You must run Alembic commands from the `alembic/` folder since that's where `alembic.ini` is located.

---

## Configuration Files

### alembic.ini
- Main configuration file
- `sqlalchemy.url` is set dynamically from `.env.local`
- No need to edit manually

### alembic/env.py
- Runs during migrations
- Converts async database URL (asyncpg) to sync (psycopg2) for Alembic
- Imports all your models for change detection

### alembic/versions/
- Contains all migration files
- Each file has `upgrade()` and `downgrade()` functions
- Always review auto-generated migrations before running

---

## Models Included

The following models are currently tracked by Alembic:

- **users.py**: User, Role management
- **project.py**: Project data
- **emissions_entries.py**: EmissionEntry, EmissionEntrySummary
- **lookup_data.py**: EmissionsCategory, EmissionsSubCategory, MeasurementUnit, EmissionSource, EmissionFactor, EmissionFactorValue
- **project_reporting_submission.py**: ProjectReportingSubmission

When you add new models, you must add their imports to `alembic/env.py`:
```python
from models.your_new_model import YourNewModel
```

---

## Key Points to Remember

✅ **DO:**
- Review migrations before applying
- Commit migration files to version control
- Use descriptive messages: `alembic revision --autogenerate -m "Add status field to projects"`
- Test migrations locally first before production

❌ **DON'T:**
- Manually edit database without migrations (defeats the purpose)
- Run migrations on production without testing first
- Ignore migration errors
- Leave migrations untracked in git

---

## Troubleshooting

### Migration not detecting changes
- Ensure your model has `__tablename__` defined
- Check that the model class inherits from `Base`
- Make sure the model is imported in `alembic/env.py`

### "No new upgrades" message
- Run `alembic current` to check current version
- Changes might already be applied or not yet generated

### Database connection errors
- Verify `.env.local` has correct `DATABASE_URL`
- Ensure PostgreSQL is running
- Check credentials are correct

---

## Example Workflow

```bash
# 1. Update a model
# (Edit models/project.py - add new field)

# 2. Navigate to alembic folder
cd backend/alembic

# 3. Generate migration
alembic revision --autogenerate -m "Add budget field to project"

# 4. Review the generated file
code versions/xxxx_add_budget_field_to_project.py

# 5. Apply the migration
alembic upgrade head

# 6. Commit to version control
git add alembic/
git commit -m "chore: Add budget field to project"
```

---

## What Happens at Each Step

### When you run `alembic revision --autogenerate -m "..."`
1. Alembic connects to your database
2. Reads your SQLAlchemy models from code
3. Compares model definitions with database schema
4. Generates Python code to transform database → model definition
5. Creates a new file in `alembic/versions/`

### When you run `alembic upgrade head`
1. Connects to database
2. Checks `alembic_version` table to see current state
3. Runs all migrations newer than current version
4. Updates `alembic_version` table with new version

### When you run `alembic stamp head`
1. Updates `alembic_version` table
2. Marks database as up-to-date without running migrations
3. Used when adopting Alembic for existing database (already done!)

---

## Next Steps

You're all set! Start using Alembic for all future schema changes:

1. Modify your SQLAlchemy models in `models/`
2. Run `alembic revision --autogenerate -m "Description"`
3. Review the generated migration
4. Run `alembic upgrade head`
5. Commit to git

This approach ensures your database schema stays in sync with your application code! 🚀
