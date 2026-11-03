# PostgreSQL integration tests

These tests run only when `CMRT_TEST_DATABASE_URL` is explicitly set. The fixture
accepts only a local PostgreSQL host and a database named `cmrt_test`; it does
not read `backend/.env.local` or the application `DATABASE_URL` setting.

Create a disposable local database and apply the project migrations before
running the integration tests. For example, from `backend/` in PowerShell:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/cmrt_test"
$env:CMRT_TEST_DATABASE_URL = $env:DATABASE_URL
$env:JWT_SECRET = "local-test-only-secret"
$env:SUPER_ADMIN_EMAIL = "test-admin@example.invalid"
alembic upgrade heads
python -m pytest -m integration
```

Each test uses an outer transaction and rolls it back, so test rows are not
committed. The database itself must still be disposable; never point this URL at
a developer database containing application data or a hosted environment.
