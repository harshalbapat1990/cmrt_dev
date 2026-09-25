# CMRT Azure Deployment

This Pulumi project provisions the CMRT Azure infrastructure, including:

- Azure Container Registry
- Azure Container Apps environment
- Private (internal-only) Backend Container App for FastAPI
- Public Frontend Container App for the React/Vite SPA, with a server-side proxy
- Azure Database for PostgreSQL Flexible Server
- Log Analytics
- Azure Easy Auth configuration on the frontend Container App only

## Authentication Architecture

Authentication happens once, at the public frontend boundary. The backend is private
infrastructure and performs authorization only — it does not authenticate anyone.

```text
Internet
  |
  v
Frontend Container App
  |
  | Azure Easy Auth
  | Auth0 as OIDC Provider
  |
  v
React SPA (static assets) + server.js (same container)
  |
  | server.js proxies /api/* over the Container Apps Environment's
  | internal network, forwarding only Azure Easy Auth identity headers
  v
Private Backend Container App (internal ingress only)
  |
  v
Authorization Layer (FastAPI: user lookup, roles, permissions, registration)
  |
  v
Database
```

Auth0 is configured only as Azure Easy Auth's custom OpenID Connect identity provider on
the frontend Container App. The frontend image must not receive Auth0 domains, client
IDs, callback URLs, or logout URLs — React never talks to Auth0 or builds `/.auth/*` URLs
itself (logout simply navigates to the same-origin `/.auth/logout`, which Azure intercepts).

### Identity propagation

1. Azure Easy Auth authenticates the browser against Auth0 before any request reaches the
   frontend container.
2. Azure injects `X-MS-CLIENT-PRINCIPAL*` headers into requests that reach the frontend
   container.
3. `client/server.js` serves the built SPA and proxies same-origin `/api/*` calls to the
   private backend's internal FQDN (`BACKEND_BASE_URL`), forwarding only the
   `x-ms-client-principal`, `x-ms-client-principal-id`, `x-ms-client-principal-name`, and
   `x-ms-client-principal-idp` headers.
4. FastAPI trusts those forwarded headers to resolve the user, then applies existing
   authorization: registration checks, organization lookup, roles, and permissions.

The backend's `AUTH_MODE=forwarded_identity` env var reflects this: the backend does not
run Easy Auth and does not validate Auth0 tokens itself.

## Required Environment Variables

Set these before running `pulumi up`:

```bash
export DATABASE_URL="..."
export JWT_SECRET="..."
export SUPER_ADMIN_EMAIL="..."
export POSTGRES_USER="..."
export POSTGRES_PASSWORD="..."
export AUTH0_DOMAIN="..."
export AUTH0_CLIENT_ID="..."
export AUTH0_CLIENT_SECRET="..."
```

`AUTH0_*` values are used only in the frontend Container App's Azure Easy Auth resource
configuration. They are not injected into the React or FastAPI application containers.

## Easy Auth Behavior

- Frontend Container App: unauthenticated requests redirect to Auth0 through Azure Easy Auth before React loads.
- Backend Container App: has no Easy Auth config and is not publicly reachable (`ingress.external_enabled=False`).
- FastAPI resolves users from identity headers forwarded by `client/server.js` and keeps existing authorization, organization, role, permission, and onboarding logic.

## Deploy

```bash
pulumi up
```

## Outputs

- `container_app_url` - backend Container App internal-only FQDN (not publicly reachable)
- `frontend_app_url` - frontend Container App public FQDN
