import pulumi
import pulumi_azure as azure
import os
# ============================================================
# RESOURCE GROUP
# ============================================================

rg = azure.core.ResourceGroup(
    "cmrt-rg-demo",
    name="cmrt-rg-demo",
    location="Australia East"
)

# ============================================================
# AZURE CONTAINER APP
# ============================================================

acr = azure.containerservice.Registry("acr",
    name="cmrtacr",
    resource_group_name=rg.name,
    location=rg.location,
    sku="Premium",
    admin_enabled=False,
    georeplications=[
    ])

# ============================================================
# NETWORKING
# ============================================================

vnet = azure.network.VirtualNetwork(
    "cmrt-vnet",
    name="cmrt-vnet",
    location=rg.location,
    resource_group_name=rg.name,
    address_spaces=["10.0.0.0/16"],
)

# ============================================================
# SUBNET FOR POSTGRES
# ============================================================

postgres_subnet = azure.network.Subnet(
    "cmrt-postgres-subnet",
    name="cmrt-postgres-subnet",
    resource_group_name=rg.name,
    virtual_network_name=vnet.name,
    address_prefixes=["10.0.2.0/24"],
    service_endpoints=["Microsoft.Storage"],
    delegations=[{
        "name": "postgres-delegation",
        "service_delegation": {
            "name": "Microsoft.DBforPostgreSQL/flexibleServers",
            "actions": [
                "Microsoft.Network/virtualNetworks/subnets/join/action"
            ],
        },
    }],
)

# ============================================================
# PRIVATE DNS ZONE FOR POSTGRES
# ============================================================

postgres_dns_zone = azure.privatedns.Zone(
    "cmrt-postgres-dns-zone",
    name="cmrt.postgres.database.azure.com",
    resource_group_name=rg.name,
)

postgres_dns_zone_vnet_link = azure.privatedns.ZoneVirtualNetworkLink(
    "cmrt-postgres-dns-link",
    name="cmrt-postgres-dns-link",
    private_dns_zone_name=postgres_dns_zone.name,
    virtual_network_id=vnet.id,
    resource_group_name=rg.name,
    opts=pulumi.ResourceOptions(depends_on=[postgres_subnet])
)

# ============================================================
# FLEXIBLE POSTGRES SERVER
# ============================================================

postgres_server = azure.postgresql.FlexibleServer(
    "cmrt-postgres",
    name="cmrt-psql-server",
    resource_group_name=rg.name,
    location=rg.location,
    version="12",
    delegated_subnet_id=postgres_subnet.id,
    private_dns_zone_id=postgres_dns_zone.id,
    public_network_access_enabled=False,
    administrator_login=os.getenv("POSTGRES_USER"),
    administrator_password=os.getenv("POSTGRES_PASSWORD"),
    zone="1",
    storage_mb=32768,
    storage_tier="P4",
    sku_name="B_Standard_B1ms",
    opts=pulumi.ResourceOptions(depends_on=[postgres_dns_zone_vnet_link]),
)

# ============================================================
# CONTAINER APPS – NETWORKING
# ============================================================

aca_subnet = azure.network.Subnet(
    "cmrt-aca-subnet",
    name="cmrt-aca-subnet",
    resource_group_name=rg.name,
    virtual_network_name=vnet.name,
    address_prefixes=["10.0.4.0/23"],
)

# ============================================================
# LOG ANALYTICS WORKSPACE
# ============================================================

analytics_workspace = azure.operationalinsights.AnalyticsWorkspace(
    "cmrt-law",
    name="cmrt-law",
    location=rg.location,
    resource_group_name=rg.name,
    sku="PerGB2018",
    retention_in_days=30,
)

# ============================================================
# CONTAINER APPS ENVIRONMENT
# ============================================================

aca_env = azure.containerapp.Environment(
    "cmrt-demo-aca-env",
    name="cmrt-demo-aca-env",
    location=rg.location,
    resource_group_name=rg.name,
    infrastructure_subnet_id=aca_subnet.id,
    logs_destination="log-analytics",
    log_analytics_workspace_id=analytics_workspace.id,
)

# ============================================================
# SUBNET FOR POSTGRES
# ============================================================

ag_subnet = azure.network.Subnet(
    "cmrt-ag-subnet",
    name="cmrt-ag-subnet",
    resource_group_name=rg.name,
    virtual_network_name=vnet.name,
    address_prefixes=["10.0.6.0/24"],
)

# ============================================================
# PRIVATE DNS ZONE FOR ag
# ============================================================

ag_dns_zone = azure.privatedns.Zone(
    "cmrt-ag-dns-zone",
    name="cmrt.applicationgateway.azure.com",
    resource_group_name=rg.name,
)

ag_dns_zone_vnet_link = azure.privatedns.ZoneVirtualNetworkLink(
    "cmrt-ag-dns-link",
    name="cmrt-ag-dns-link",
    private_dns_zone_name=ag_dns_zone.name,
    virtual_network_id=vnet.id,
    resource_group_name=rg.name,
    opts=pulumi.ResourceOptions(depends_on=[ag_subnet])
)

# ============================================================
# BACKEND CONTAINER APP
# ============================================================

container_app = azure.containerapp.App(
    "cmrt-app",
    name="cmrt-app",
    resource_group_name=rg.name,
    container_app_environment_id=aca_env.id,
    revision_mode="Single",
    registries=[{
        "server": acr.login_server,
        "identity": "system",
    }],
    ingress={
        # Internal-only: the backend is private infrastructure, reachable only
        # from other apps in this Container Apps Environment (i.e. the frontend).
        "external_enabled": False,
        "target_port": 8000,
        "traffic_weights": [{"latest_revision": True, "percentage": 100}],
    },
    identity={"type": "SystemAssigned"},
    templates=[{
        "containers": [{
            "name": "cmrt-backend",
            "image": acr.login_server.apply(lambda s: f"{s}/cmrt_backend_app:latest"),
            "cpu": 0.5,
            "memory": "1Gi",
            "envs": [
                # Backend trusts identity forwarded by the frontend's private-network
                # proxy; it does not run its own Easy Auth or validate Auth0 tokens.
                {"name": "AUTH_MODE",       "value": "forwarded_identity"},
                {"name": "DATABASE_URL",    "secret_name": "database-url"},
                {"name": "JWT_SECRET",      "secret_name": "jwt-secret"},
                {"name": "SUPER_ADMIN_EMAIL", "value": os.getenv("SUPER_ADMIN_EMAIL", "")},
            ],
        }],
        "min_replicas": 1,
        "max_replicas": 3,
    }],
    secrets=[
        {"name": "database-url", "value": os.getenv("DATABASE_URL", "")},
        {"name": "jwt-secret",   "value": os.getenv("JWT_SECRET", "")},
    ],
)

# ============================================================
# FRONTEND CONTAINER APP
# ============================================================

frontend_app = azure.containerapp.App(
    "cmrt-frontend-app",
    name="cmrt-frontend-app",
    resource_group_name=rg.name,
    container_app_environment_id=aca_env.id,
    revision_mode="Single",
    registries=[{
        "server": acr.login_server,
        "identity": "system",
    }],
    ingress={
        "external_enabled": True,
        "target_port": 5173,
        "traffic_weights": [{"latest_revision": True, "percentage": 100}],
    },
    identity={"type": "SystemAssigned"},
    templates=[{
        "containers": [{
            "name": "cmrt-frontend",
            "image": acr.login_server.apply(lambda s: f"{s}/cmrt_frontend_app:latest"),
            "cpu": 0.5,
            "memory": "1Gi",
            "envs": [
                # Internal FQDN of the private backend Container App — server.js
                # proxies browser /api/* calls here and forwards identity headers.
                {"name": "BACKEND_BASE_URL", "value": container_app.latest_revision_fqdn.apply(lambda fqdn: f"https://{fqdn}")},
            ],
        }],
        "min_replicas": 1,
        "max_replicas": 3,
    }],
    secrets=[
        {"name": "auth0-client-secret", "value": os.getenv("AUTH0_CLIENT_SECRET", "")},
    ],
)

# ============================================================
# EASY AUTH — Auth0 as Azure-managed custom OIDC provider
# Authentication happens ONLY at the frontend Container App boundary. The
# backend has no Easy Auth config: it is private infrastructure that trusts
# identity headers forwarded by the frontend's server-side proxy.
# Uses an ARM template deployment because pulumi_azure (classic)
# does not yet expose Microsoft.App/containerApps/authConfigs.
# Set AUTH0_CLIENT_SECRET in the environment before running pulumi up.
# ============================================================

frontend_auth_config = azure.core.ResourceGroupTemplateDeployment(
        "cmrt-frontend-easy-auth",
        resource_group_name=rg.name,
        deployment_mode="Incremental",
        template_content=frontend_app.name.apply(lambda app_name: f"""{{
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "resources": [
        {{
            "type": "Microsoft.App/containerApps/authConfigs",
            "apiVersion": "2024-03-01",
            "name": "{app_name}/current",
            "properties": {{
                "platform": {{ "enabled": true }},
                "globalValidation": {{
                    "unauthenticatedClientAction": "RedirectToLoginPage",
                    "redirectToProvider": "auth0"
                }},
                "identityProviders": {{
                    "customOpenIdConnectProviders": {{
                        "auth0": {{
                            "registration": {{
                                "clientId": "{os.getenv('AUTH0_CLIENT_ID', '')}",
                                "clientCredential": {{ "secretSettingName": "auth0-client-secret" }},
                                "openIdConnectConfiguration": {{
                                    "wellKnownOpenIdConfiguration": "https://{os.getenv('AUTH0_DOMAIN', '')}/.well-known/openid-configuration"
                                }}
                            }},
                            "login": {{ "scopes": ["openid", "profile", "email"] }}
                        }}
                    }}
                }},
                "login": {{
                    "preserveUrlFragmentsForLogins": false
                }}
            }}
        }}
    ]
}}"""),
        opts=pulumi.ResourceOptions(depends_on=[frontend_app]),
)

# container_app_url is an internal-only FQDN — the backend is not publicly reachable.
pulumi.export("container_app_url", container_app.latest_revision_fqdn)
pulumi.export("frontend_app_url", frontend_app.latest_revision_fqdn)
