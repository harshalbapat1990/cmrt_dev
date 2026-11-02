
import { useEffect, useState } from "react";
import EmptyOverview from "./EmptyHomePage";
import AdminProjects from "./projects/AdminProjects";
import UserProjects from "./projects/UserProjects";
import { useUser } from "../../context/UserContext";
import http from "@/http";
import ProjectAccessService from "@/services/ProjectAccess.service";
import type { Project } from "../../types/project";

interface ProjectApiRow {
  id: string;
  project_name: string;
  program_name: string | null;
  project_class: string | null;
  updated_on: string;
  created_on:string | null;
  is_active: boolean | null;
  has_entries: boolean;
}

function mapToProject(p: ProjectApiRow, access: "view" | "edit"): Project {
  const status = !p.is_active
    ? "Closed"
    : p.has_entries
      ? "In Progress"
      : "Not Started";
  return {
    id: p.id,
    projectName: p.project_name,
    programName: p.program_name ?? "",
    category: p.project_class ?? "",
    emissions: 0,
   lastUpdated: p.updated_on ?? p.created_on ?? "-",
    status,
    statusNote: "",
    access,
  };

}

export default function HomePage() {
  const { roles, isLoaded } = useUser();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const isOrgAdmin = roles.includes("ORG_ADMIN");
  const isProjAdmin = roles.includes("PROJECT_ADMIN");
  const fallbackAccess: "view" | "edit" =
    isOrgAdmin || roles.includes("PROJECT_ADMIN") ? "edit" : "view";

  useEffect(() => {
    if (!isLoaded) return;
    setLoading(true);
    http
      .get<ProjectApiRow[]>("/api/me/projects")
      .then(async (res) => {
        const mapped = await Promise.all(
          res.data.map(async (p) => {
            try {
              const access = await ProjectAccessService.fetchMyProjectAccess(p.id);
              const canEdit = access.stage_access.some(
                (stage) => stage.access === "EDIT" || stage.access === "ADMIN",
              );
              return mapToProject(p, canEdit ? "edit" : "view");
            } catch {
              return mapToProject(p, fallbackAccess);
            }
          }),
        );
        setProjects(mapped);
      })
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, [isLoaded, roles]);

  if (!isLoaded || loading) {
    return <div className="p-8 text-slate-400">Loading…</div>;
  }

  const hasProjects = projects.length > 0;

  if (!hasProjects) {
    return (
      <div>
        <EmptyOverview role={isOrgAdmin ? "admin" : "user"} />
      </div>
    );
  }

  if (isOrgAdmin) {
    return (
      <div>
        <AdminProjects data={projects} role="Org admin" />
      </div>
    );
  }

  if (isProjAdmin) {
    return (
      <div>
        <AdminProjects data={projects} role="Project admin" />
      </div>
    );
  }

  return (
    <div>
      <UserProjects data={projects} />
    </div>
  );
}

