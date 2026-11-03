# Codebase cleanup and security audit

Audit date: 2026-11-03

## Deployment and repository inventory

- The active deployment workflow is `.github/workflows/deploy-to-acr.yml`. It builds the root `backend/Dockerfile` and `client/Dockerfile`; the backend image starts through `backend/entrypoint.sh`, which applies Alembic migrations.
- The root `backend/app/main.py` registers the FastAPI routers. The client uses `client/package.json` and `client/package-lock.json`.
- `backend/alembic/versions/` contains schema and data migrations and is retained. Tests, data files referenced by runtime code, Dockerfiles, deployment configuration, and generated client assets were not deleted based on size or age.
- The root `app/`, root `Dockerfile`, `pyproject.toml`, and `uv.lock` form a separate FastHTML/DuckDB prototype and dependency set. The deployment workflow does not build it, but the root Dockerfile can still be used manually. They are retained pending confirmation that nobody still uses this prototype. The root `README.md` is empty but is referenced by `pyproject.toml`, so it is also retained.
- Root `package-lock.json` had an empty package list and no root `package.json`; it was confirmed orphaned and deleted. The active client lockfile remains.

## Deletions

The exact path and reason for every deleted tracked file is listed in [codebase-cleanup-deletion-manifest.txt](codebase-cleanup-deletion-manifest.txt).

- Deleted the nested `cmrt_dev-dropdown-fixes-for-datasets/` checkout: 1,311 tracked paths. It had no unique paths, and the root deployment uses root-level `backend/` and `client/`.
- Deleted `commit_fb5e7cd.zip` (empty) and `database_state_report.txt` (unreferenced generated report).
- Deleted the root `package-lock.json` orphan (no matching root package manifest).
- Total manifest entries: 1,314 tracked file paths.

`backend/.venv-auth-check/` remains as a review item. It is a tracked virtual environment tied to an unavailable Python 3.12 installation. The safety review did not authorize its deletion; confirm whether to remove or retain it.

## Findings and remediation

### Resolved during this audit

1. **Header disclosure endpoint in the standalone prototype.** The unauthenticated `/debug/headers` route returned all request headers, which could include bearer or proxy identity credentials. The route was removed from `app/app.py`.
2. **SQL injection in prototype identity lookup.** `check_user_auth` interpolated a request-derived user identifier into a DuckDB query. It now passes the value as a bound query parameter.
3. **TLS verification bypass in the prototype Docker build.** The root `Dockerfile` passed `--trusted-host` for package indexes. These flags were removed; pip now uses normal TLS validation.
4. **Unauthenticated prototype handlers.** All mutation and conversion HTTP handlers, plus the WebSocket, now validate the same identity against the configured user directory before use. Malformed or unavailable identity data fails closed.

### High priority: unresolved before exposing the standalone prototype

The root FastHTML prototype trusts `X-MS-CLIENT-PRINCIPAL` as an ingress-provided identity, as its existing home-page check did. Its handlers now validate that identity for every HTTP operation and WebSocket connection. That header is not cryptographically verified by this application, so a direct public connection that bypasses Azure Easy Auth or an equivalent trusted proxy can spoof it. No root deployment workflow currently deploys this image, so the prototype was retained rather than silently removed. Keep it behind a trusted identity proxy or retire it before exposing the root Docker image directly.

## Security scan baseline

Two CI workflows now provide repeatable scans:

- `.github/workflows/security-scans.yml` runs `npm audit` for the client, `pip-audit` for the active backend, standalone prototype, and Pulumi deployment requirements, and Gitleaks over the checked-out files and all Git history/refs.
- `.github/workflows/codeql.yml` runs GitHub CodeQL security-extended analysis for Python and JavaScript/TypeScript on pull requests, deployment branches, and a weekly schedule.

The scans have not run in this local environment yet. Gitleaks, pip-audit, and CodeQL are not installed locally; `npm audit` could not reach the package registry from this workspace. Therefore this report does **not** claim that the repository is free of secrets or known dependency vulnerabilities. Review the CI results before treating the scan baseline as clean. Secret findings should be handled without copying secret values into reports; rotate any confirmed credential that was committed.

## Static review limits and next actions

- Pattern searches for `shell=True`, `verify=False`, unsafe deserialization, and direct string-built SQL were used as triage, not as proof of safety. Matches were reviewed where relevant; generated SQL and ordinary `exec`/regex matches are not automatically vulnerabilities.
- Review the CodeQL, Gitleaks, and dependency scan results on the first CI run. Fix confirmed high-severity findings, then triage lower-severity results for compatibility and upgrade risk.
- Decide whether the standalone prototype should be retired or brought under the same authenticated deployment boundary as the main application.
- Decide whether the broken tracked `backend/.venv-auth-check/` directory should be removed. It is not included in the deletion manifest because deletion was not approved by the safety review.
- Consider adding secret scanning protection in GitHub repository settings and requiring these security workflows on protected branches.

## Validation results

- Client tests: **88 files, 250 tests passed** with Vitest limited to two workers. The default unbounded-worker run was stopped after remaining silent; the bounded run completed successfully.
- Client test TypeScript check: passed.
- Client production build: passed.
- Client lint: passed with **88 existing warnings**. Two `no-useless-catch` errors in `ReportingBoundaryActivity.tsx` were removed during this audit.
- Prototype Python syntax parse and both security workflow YAML parses: passed.
- Backend pytest could not run because pytest is not installed in the available Python environment.
- Local `npm audit` could not reach the npm registry. Dependency and secret scan results remain pending the new CI workflows.
