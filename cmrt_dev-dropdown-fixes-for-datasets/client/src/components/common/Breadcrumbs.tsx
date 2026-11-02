import { Link, useLocation } from "react-router-dom";
import { useProjectHeader } from "../../context/ProjectHeaderContext";
import { useUser } from "@/context/UserContext";

// Generic label map used by the fallback segment expander for routes not in ROUTE_BREADCRUMBS.
const breadcrumbNameMap: Record<string, string> = {
  "/home": "Projects",
  "/overview": "Overview",
  "/datasets": "Datasets",
  "/datasets/org": "Organisation Datasets",
  "/datasets/project": "Project Datasets",
  "/user-guide": "User Guide",
  "/newproject": "New Project Setup",
  "/addnewproject": "New Project Setup",
  "/monthlyreport": "Monthly Report",
  "/profile": "Profile",
  "/projects": "Projects",
  "/manageusaraccess": "Manage User Access",
  "/audit": "Audit Log",
};

const linkOverrides: Record<string, string> = {
  "/projects": "/Home/",
};

// Token placeholders resolved at render time from context.
// Each entry is an ordered list of crumbs: { label, to? }.
// Last crumb is always rendered as plain text (current page).
// Use {{projectName}}, {{projectLink}}, {{orgName}} as dynamic tokens.
type CrumbDef = { label: string; to?: string };

const ROUTE_BREADCRUMBS: Record<string, CrumbDef[]> = {
  // Single-label routes (home / manage access role variants)
  "/home":                        [{ label: "Projects" }],
  "/home/admin":                  [{ label: "Projects" }],
  "/home/user":                   [{ label: "Projects" }],
  "/manageusaraccess/admin":      [{ label: "Manage User Access" }],
  "/manageusaraccess/orgadmin":   [{ label: "Manage User Access" }],
  "/manageusaraccess/superadmin": [{ label: "Manage User Access" }],

  // Org admin results dashboard
  "/orgresultdashboard": [
    { label: "{{orgName}}" },
    { label: "Org Results Dashboard" },
  ],

  // Project-scoped routes
  "/dataentry": [
    { label: "Projects", to: "/Home/" },
    { label: "{{projectName}}", to: "{{projectLink}}" },
    { label: "Data entry" },
  ],
  "/resultsdashboard": [
    { label: "Projects", to: "/Home/" },
    { label: "{{projectName}}", to: "{{projectLink}}" },
    { label: "Results Dashboard" },
  ],
  "/resultsdashboard/detailedcalculations": [
    { label: "Projects", to: "/Home/" },
    { label: "{{projectName}}", to: "{{projectLink}}" },
    { label: "Results Dashboard", to: "/resultsDashboard/" },
    { label: "View Calculations" },
  ],
};

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const Sep = () => <span className="text-gray-400 mx-1">/</span>;

export default function Breadcrumbs() {
  const location = useLocation();
  const { projectName, projectId } = useProjectHeader();
  const { user } = useUser();

  if (location.pathname === "/") return null;

  const pathLower = location.pathname.toLowerCase().replace(/\/$/, "");

  const tokens: Record<string, string> = {
    "{{projectName}}": projectName ?? "Project",
    "{{projectLink}}": projectId ? `/projects/${projectId}` : "/Home/",
    "{{orgName}}": user?.organisation_name ?? "Organisation",
  };
  const resolve = (s: string) => tokens[s] ?? s;

  const crumbs = ROUTE_BREADCRUMBS[pathLower];
  if (crumbs) {
    return (
      <nav aria-label="Breadcrumb" className="text-sm text-gray-500">
        <ol className="flex items-center">
          {crumbs.map((crumb, idx) => {
            const isLast = idx === crumbs.length - 1;
            const label = resolve(crumb.label);
            const to = crumb.to ? resolve(crumb.to) : undefined;
            return (
              <li key={idx} className="flex items-center">
                {idx > 0 && <Sep />}
                {!isLast && to ? (
                  <Link to={to} className="hover:text-primary">{label}</Link>
                ) : (
                  <span className="text-gray-700 font-medium">{label}</span>
                )}
              </li>
            );
          })}
        </ol>
      </nav>
    );
  }

  // Fallback: expand path segments for routes not explicitly listed above.
  const pathnames = location.pathname.split("/").filter(Boolean);
  let accumulated = "";

  return (
    <nav aria-label="Breadcrumb" className="text-sm text-gray-500">
      <ol className="flex items-center">
        {pathnames.map((segment, idx) => {
          accumulated += `/${segment}`;
          const isLast = idx === pathnames.length - 1;
          const lookupKey = accumulated.toLowerCase();
          const isUUID = UUID_RE.test(segment);
          const label = isUUID && projectName
            ? projectName
            : (breadcrumbNameMap[lookupKey] ?? segment);
          return (
            <li key={accumulated} className="flex items-center">
              {idx > 0 && <Sep />}
              {isLast ? (
                <span className="text-gray-700 font-medium">{label}</span>
              ) : (
                <Link to={linkOverrides[lookupKey] ?? accumulated} className="hover:text-primary">{label}</Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}