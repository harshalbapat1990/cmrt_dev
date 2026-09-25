import React, { useEffect, useMemo, useRef, useState } from "react";
import type { OrgAdminAccessRequest, AdminAccessRequest } from "../../types/access";
import { useToast } from "../../components/common/ToastProvider";
import alertIconUrl from "../../assets/icons/emergency_home.svg";
import editIconUrl from '../../assets/icons/edit.svg';
import SearchInput from "../../components/SearchInput";
import useDebounce from "../../customHooks/useDebounce";
import accessRequestsService from "../../services/accessRequests.service";
import userRolesService, { type UserRoleEnriched } from "../../services/userRoles.service";
import orgAdminService from "@/services/orgAdmin.service";
import AccessTable from "../../components/AccessTable";
import ReviewModal from "../../components/ReviewModal";
import { useUser } from "@/context/UserContext";
import StageAccessManager from "@/components/StageAccessManager";

import http from "@/http";

export type DisplayOrgUser = {
  id: string;
  name: string;
  email: string;
  dateJoined: string;
  project_roles?: Array<{
    project_id: string;
    project_name: string;
    role_name: string;
    user_role_id: string;
    is_active: boolean;
  }>;
  has_org_admin_role?: boolean;
  org_admin_user_role_id?: string;
};

const th =
  "px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-text-base bg-[#F7F7F7]";
const td =
  "px-4 py-3 text-sm text-text-dark  align-middle";

const OrgAdminAccessPage: React.FC = () => {
  const { success, error } = useToast();
  const { user: currentUser } = useUser();
  type TabKey = "org" | "projects";
  const [tab, setTab] = useState<TabKey>("org");

  type OrgScreen = "cards" | "review" | "projectAdmins" | "orgUsers";
  const [orgScreen, setOrgScreen] = useState<OrgScreen>("cards");

  type ProjScreen = "cards" | "manage" | "review";
  const [projScreen, setProjScreen] = useState<ProjScreen>("cards");

  const [orgItems, setOrgItems] = useState<OrgAdminAccessRequest[]>([]);
  const [, setOrgLoading] = useState(true);

  const [assignProjectId, setAssignProjectId] = useState<string | null>(null);
  const [assignProjectName, setAssignProjectName] = useState<string | null>(null);
  const [orgUsers, setOrgUsers] = useState<DisplayOrgUser[]>([]);
  

  const isAssignModalOpen = Boolean(assignProjectId);

  useEffect(() => {
    let cancelled = false;
    setOrgLoading(true);
    accessRequestsService
      .fetchPending()
      .then((raw) => {
        if (cancelled) return;
        const projectAdminOnly = raw.filter((r: any) => r.request_type === "PROJECT_ADMIN");
        setOrgItems(
          projectAdminOnly.map((r: any) => ({
            id: r.id,
            requestedBy: r.requester_display_name || r.requester_email || "Unknown",
            email: r.requester_email || "",
            projectName: r.project_name || "",
            dateRequested: r.created_on || "",
            justification: r.reason,
            requestedRole: r.request_type,
            action: "Review request",
          }))
        );
      })
      .catch(() => {
        if (!cancelled) error("Failed to load access requests.");
      })
      .finally(() => {
        if (!cancelled) setOrgLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);


  useEffect(() => {
    let cancelled = false; 
    orgAdminService
      .fetchOrgUsers() 
      .then((usersFromApi) => {
        if (cancelled) return;
        setOrgUsers(
          usersFromApi.map((u: any) => ({
            id: u.id,
            name: u.display_name || u.name || u.email || "Unknown",
            email: u.email,
            dateJoined: u.date_joined
              ? formatDate(u.date_joined)
              : (u.dateJoined || ""),
            project_roles: u.project_roles || [],
            has_org_admin_role: u.has_org_admin_role ?? false,
            org_admin_user_role_id: u.org_admin_user_role_id,
          }))
        );
      })
      .catch(() => {
        if (!cancelled) error("Failed to load organisation users");
      });
      
    return () => {
      cancelled = true;
    };
  }, []); 

 const refreshOrgUsers = async () => {
  try {
    const usersFromApi = await orgAdminService.fetchOrgUsers(true);
    setOrgUsers(
      usersFromApi.map((u: any) => ({
        id: u.id,
        name: u.display_name || u.name || u.email || "Unknown",
        email: u.email,
        dateJoined: u.date_joined
          ? formatDate(u.date_joined)
          : "",
        project_roles: u.project_roles || [],
        has_org_admin_role: u.has_org_admin_role ?? false,
        org_admin_user_role_id: u.org_admin_user_role_id,
      }))
    );
  } catch {
    error("Failed to refresh organisation users");
  }
};

  
  type SortDir = "asc" | "desc";
  const [orgSortDir, setOrgSortDir] = useState<SortDir>("desc");

  function parseDate(dateStr: string): number {
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? 0 : d.getTime();
  }

  const sortedOrgReview = useMemo(() => {
    return [...orgItems].sort((a, b) => {
      const at = parseDate(a.dateRequested);
      const bt = parseDate(b.dateRequested);
      const cmp = at === bt ? 0 : at < bt ? -1 : 1;
      return orgSortDir === "asc" ? cmp : -cmp;
    });
  }, [orgItems, orgSortDir]);

  const toggleOrgDateSort = () => setOrgSortDir((d) => (d === "asc" ? "desc" : "asc"));

  const [orgOpen, setOrgOpen] = useState(false);
  const [orgSelected, setOrgSelected] = useState<OrgAdminAccessRequest | null>(null);

  const openOrgModal = (r: OrgAdminAccessRequest) => {
    setOrgSelected(r);
    setOrgOpen(true);
  };
  const closeOrgModal = () => {
    setOrgOpen(false);
    setTimeout(() => setOrgSelected(null), 200);
  };

  const handleOrgApprove = async (r: OrgAdminAccessRequest) => {
    try {
      await accessRequestsService.approve(r.id);
      setOrgItems((prev) => prev.filter((x) => x.id !== r.id));
      success(`Access request for ${r.requestedBy} has been approved`);
      if (r.requestedRole === "PROJECT_ADMIN") refreshProjectAdmins();
    } catch (e: any) {
      if (e?.response?.status === 409) {
        setOrgItems((prev) => prev.filter((x) => x.id !== r.id));
        error("This request was already reviewed by another admin.");
      } else {
        error("Failed to approve. Please try again.");
      }
    } finally {
      closeOrgModal();
    }
  };

  const handleOrgReject = async (r: OrgAdminAccessRequest, reason: string) => {
    try {
      await accessRequestsService.reject(r.id, reason);
      setOrgItems((prev) => prev.filter((x) => x.id !== r.id));
      success(`Access request for ${r.requestedBy} has been rejected`);
    } catch (e: any) {
      if (e?.response?.status === 409) {
        setOrgItems((prev) => prev.filter((x) => x.id !== r.id));
        error("This request was already reviewed by another admin.");
      } else {
        error("Failed to reject. Please try again.");
      }
    } finally {
      closeOrgModal();
    }
  };
 
  const handleAddAdmin = (projectId: string, projectName: string) => {
    setAssignProjectId(projectId);
    setAssignProjectName(projectName);
  };

  const handleCloseAssignModal = () => {
    setAssignProjectId(null);
    setAssignProjectName(null);
  };

  
  async function handleAssignAdmin(userId: string) {
    if (!assignProjectId) return;

    try {
      await orgAdminService.addProjectAdmin(assignProjectId, userId);
      success(`Project administrator assigned to ${assignProjectName}`);
      await Promise.all([
        orgAdminService.fetchOrgUsers(true), 
        refreshProjectAdmins() 
      ]);
      
      handleCloseAssignModal();
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || err?.message || "Failed to assign project administrator.";
      error(errorMessage);
    }
  }

  async function handleRemoveAdmin(projectId: string, userId: string) {
    try {
      await orgAdminService.removeProjectAdmin(projectId, userId);
      success("Project administrator removed");
      await Promise.all([
        orgAdminService.fetchOrgUsers(true), 
        refreshProjectAdmins()
      ]);
    } catch (err: any) {
      const errorMessage = err?.response?.data?.message || err?.message || "Failed to remove project administrator";
      error(errorMessage);
    }
  }

  const [projectAdminProjects, setProjectAdminProjects] = useState<
    { id: string; name: string; admins: UserRoleEnriched[] }[]
  >([]);
  const [projectAdminsLoading, setProjectAdminsLoading] = useState(true);

  const refreshProjectAdmins = React.useCallback(async () => {
    setProjectAdminsLoading(true);

    try {
      const [projectsResponse, adminRoles] = await Promise.all([
        http.get("/api/me/projects"),
        userRolesService.fetchEnriched({
          scope_type: "PROJECT",
          role_name: "PROJECT_ADMIN",
          limit: 500,
        }),
      ]);

      const projects: any[] = projectsResponse.data ?? [];


      const adminsByProjectId: Record<string, UserRoleEnriched[]> = {};

      for (const ur of adminRoles) {
        if (!ur.scope_id) continue;

        if (!adminsByProjectId[ur.scope_id]) {
          adminsByProjectId[ur.scope_id] = [];
        }

        adminsByProjectId[ur.scope_id].push(ur);
      }

      setProjectAdminProjects(
        projects
          .map((project) => ({
            id: project.id,
            name: project.project_name || "Unknown Project",
            admins: adminsByProjectId[project.id] ?? [],
          }))
          .sort((a, b) => a.name.localeCompare(b.name))
      );
    } catch {
      error("Failed to load project administrators.");
      setProjectAdminProjects([]);
    } finally {
      setProjectAdminsLoading(false);
    }
  }, [error]);

  useEffect(() => {
    refreshProjectAdmins();
  }, [refreshProjectAdmins]);

  const [projItems, setProjItems] = useState<AdminAccessRequest[]>([]);
  const [, setProjLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setProjLoading(true);
    accessRequestsService
      .fetchPending()
      .then((raw) => {
        if (cancelled) return;
        const projectLevel = raw.filter((r: any) =>
          ["PROJECT_EDITOR", "PROJECT_VIEWER"].includes(r.request_type)
        );
        setProjItems(
          projectLevel.map((r: any) => ({
            id: r.id,
            requester: r.requester_display_name || r.requester_email || "Unknown",
            projectName: r.project_name || "",
            projectCategory: r.project_class ?? "",
            stages: [],
            dateRequested: r.created_on || "",
            justification: r.reason || undefined,
            requestedRole: r.request_type,
          }))
        );
      })
      .catch(() => {
        if (!cancelled) error("Failed to load access requests.");
      })
      .finally(() => {
        if (!cancelled) setProjLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const sortedProjReview = useMemo(() => {
    const arr = [...projItems];
    arr.sort((a, b) => a.dateRequested.localeCompare(b.dateRequested));
    return arr;
  }, [projItems]);

  const [projOpen, setProjOpen] = useState(false);
  const [projSelected, setProjSelected] = useState<AdminAccessRequest | null>(null);

  const openProjModal = (r: AdminAccessRequest) => {
    setProjSelected(r);
    setProjOpen(true);
  };
  const closeProjModal = () => {
    setProjOpen(false);
    setTimeout(() => setProjSelected(null), 200);
  };

  const handleProjApprove = async (r: AdminAccessRequest) => {
    try {
      await accessRequestsService.approve(r.id);
      setProjItems((prev) => prev.filter((x) => x.id !== r.id));
      success(`Access request for ${r.requester} has been approved`);
    } catch (e: any) {
      if (e?.response?.status === 409) {
        setProjItems((prev) => prev.filter((x) => x.id !== r.id));
        error("This request was already reviewed by another admin.");
      } else {
        error("Failed to approve. Please try again.");
      }
    } finally {
      closeProjModal();
    }
  };

  const handleProjReject = async (r: AdminAccessRequest, reason: string) => {
    try {
      await accessRequestsService.reject(r.id, reason);
      setProjItems((prev) => prev.filter((x) => x.id !== r.id));
      success(`Access request for ${r.requester} has been rejected`);
    } catch (e: any) {
      if (e?.response?.status === 409) {
        setProjItems((prev) => prev.filter((x) => x.id !== r.id));
        error("This request was already reviewed by another admin.");
      } else {
        error("Failed to reject. Please try again.");
      }
    } finally {
      closeProjModal();
    }
  };

  const [orgUsersSearch, setOrgUsersSearch] = useState("");
  const [orgUsersSortDir, setOrgUsersSortDir] = useState<"asc" | "desc">("asc");

  const filteredUsers = useMemo(() => {
    const q = orgUsersSearch.trim().toLowerCase();
    const list = !q
      ? orgUsers
      : orgUsers.filter(
          (u) => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
        );
    return [...list].sort((a, b) =>
      orgUsersSortDir === "asc" ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name)
    );
  }, [orgUsersSearch, orgUsersSortDir, orgUsers]);

  const toggleOrgUsersSort = () =>
    setOrgUsersSortDir((d) => (d === "asc" ? "desc" : "asc"));

  return (
    <div className="min-h-screen w-full overflow-x-hidden text-text-dark">
      <div className="mx-auto mt-8 sm:mt-12 max-w-7xl px-3 sm:px-4 md:px-6">
        <h2 className="mb-6 sm:mb-8 text-2xl sm:text-3xl font-light text-text-dark">Manage user access</h2>
        <div className="mb-6 border-b-2 border-[#ADADAD]">
          <div className="flex gap-6">
            <TabButton active={tab === "org"} onClick={() => setTab("org")}>
              Manage organisation
            </TabButton>

            <TabButton active={tab === "projects"} onClick={() => setTab("projects")}>
              Manage projects
            </TabButton>
          </div>
        </div>
        {tab === "org" ? (
          <>
            {orgScreen === "cards" && (
              <OrgCards
                onReview={() => setOrgScreen("review")}
                onProjectAdmins={() => setOrgScreen("projectAdmins")}
                onOrgUsers={() => setOrgScreen("orgUsers")}
              />
            )}

            {orgScreen === "review" && (
              <ReviewAccessRequestsView
                title="Pending requests for project administrator access "
                sorted={sortedOrgReview}
                sortDir={orgSortDir}
                toggleDateSort={toggleOrgDateSort}
                openModal={openOrgModal}
                onBack={() => setOrgScreen("cards")}
              />
            )}

            {orgScreen === "projectAdmins" && (
              <ProjectAdminsView
                projectAdminsLoading={projectAdminsLoading}
                projectAdminProjects={projectAdminProjects}
                onBack={() => setOrgScreen("cards")}
                onAddAdmin={handleAddAdmin}
                onRemoveAdmin={handleRemoveAdmin}
                assignProjectId={assignProjectId}
                assignProjectName={assignProjectName}
                isAssignModalOpen={isAssignModalOpen}
                orgUsers={orgUsers}
                onAssign={handleAssignAdmin}
                onCloseAssignModal={handleCloseAssignModal}
              />
            )}

            {orgScreen === "orgUsers" && (
              <OrgUsersView
                users={filteredUsers}
                search={orgUsersSearch}
                setSearch={setOrgUsersSearch}
                sortDir={orgUsersSortDir}
                toggleSort={toggleOrgUsersSort}
                onBack={() => setOrgScreen("cards")}
                onRefreshUsers={refreshOrgUsers}
                onMakeOrgAdmin={async (userId, userName) => {
                  await orgAdminService.addOrgAdmin(userId);
                  success(`${userName} has been assigned as Org Admin`);
                  await refreshOrgUsers();
                }}
                onRemoveOrgAdmin={async (userRoleId, userName) => {
                  await orgAdminService.removeOrgAdmin(userRoleId);
                  success(`${userName}'s Org Admin role has been removed`);
                  await refreshOrgUsers();
                }}
                currentUserId={currentUser?.user_id}
              />
            )}
          </>
        ) : (
          <>
            {projScreen === "cards" && (
              <ManageProjectsCards
                onManage={() => setProjScreen("manage")}
                onReview={() => setProjScreen("review")}
              />
            )}

            {projScreen === "manage" && (
              <>
                <BackButton onClick={() => setProjScreen("cards")} />
                <StageAccessManager />
              </>
            )}

            {projScreen === "review" && (
             <>
                <BackButton onClick={() => setProjScreen("cards")} />
                <AccessTable
                    items={sortedProjReview}
                    onOpen={openProjModal}
                    maxHeight={560}
                    sortByProp="dateRequested"
                    sortDirProp="asc"
                  />
                </>
            )}
          </>
        )}
      </div>
      <OrgAdminReviewModal
        open={orgOpen}
        request={orgSelected}
        formerror="Reason for rejection is required"
        onClose={closeOrgModal}
        onApprove={handleOrgApprove}
        onReject={handleOrgReject}
      />
      <ReviewModal
      open={projOpen}
      request={projSelected}
      formerror="Reason for rejection is required"
      onClose={closeProjModal}
      onApprove={handleProjApprove}
      onReject={handleProjReject}
    />
    </div>
  );
};

export default OrgAdminAccessPage;

function TabButton({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative -mb-px px-2 sm:px-3 py-3 cursor-pointer text-sm transition-colors ${
        active ? "font-medium text-primary" : "text-text-base hover:text-text-dark"
      }`}
      aria-current={active ? "page" : undefined}
    >
      {children}
      {active && <span className="absolute inset-x-0 -bottom-px block h-0.5 bg-primary" />}
    </button>
  );
}

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="text-primary text-sm font-medium cursor-pointer mb-4 inline-flex items-center gap-1"
    >
      <span className="material-symbols-rounded">chevron_left</span> Back
    </button>
  );
}

function OrgCards({
  onReview,
  onProjectAdmins,
  onOrgUsers,
}: {
  onReview: () => void;
  onProjectAdmins: () => void;
  onOrgUsers: () => void;
}) {
  return (
    <div className="flex gap-6">
      <Card
        title="Review access requests"
        text="Review and approve project administrator access requests"
        onClick={onReview}
      />
      <Card
        title="Manage project administrators"  
        text={
          <>
            Assign administrators to review project data submissions, and manage access.
            <br />
            <br/>
            View all projects in the organisation with their assigned administrators, and add or remove administrators as required.
          </>
        }
         onClick={onProjectAdmins}
      />
      <Card
        title="View organisation users"
        text="View and manage all users in your organisation"
        onClick={onOrgUsers}
      />
    </div>
  );
}

function ManageProjectsCards({
  onManage,
  onReview,
}: {
  onManage: () => void;
  onReview: () => void;
}) {
  return (
    <div className="flex gap-6">
      <Card
        title="Manage projects"
        text="View projects in your portfolio, review members and manage access."
        onClick={onManage}
      />
      <Card
        title="Review access requests"
        text="Review and approve or reject project access requests."
        onClick={onReview}
      />
    </div>
  );
}

function Card({
  title,
  text,
  onClick,
}: {
  title: string;
  text: React.ReactNode; 
  onClick: () => void;
}) {
  return (
    <button
      className="w-103 h-55.5 text-left flex flex-col cursor-pointer justify-start items-start border rounded-[var(--radius-3)] p-5 bg-white border-border hover:bg-[#f0f0f0]"
      onClick={onClick}
    >
      <div className="font-medium text-xl text-text-dark mb-4">
        {title}
      </div>
      <div className="text-base text-text-base">
        {text}
      </div>
    </button>
  );
}

function ReviewAccessRequestsView({
  title,
  sorted,
  sortDir,
  toggleDateSort,
  openModal,
  onBack,
}: {
  title: string;
  sorted: OrgAdminAccessRequest[];
  sortDir: "asc" | "desc";
  toggleDateSort: () => void;
  openModal: (r: OrgAdminAccessRequest) => void;
  onBack: () => void;
}) {
  return (
    <>
      <BackButton onClick={onBack} />
      <section className="overflow-hidden rounded-[var(--radius-3)] bg-white">
        <div className="px-6 py-5">
          <h3 className="text-2xl font-light text-text-dark">
            {title} ({sorted.length})
          </h3>
        </div>

        <div className="overflow-y-auto max-h-[70vh]">
          <table className="min-w-full border-separate" style={{ borderSpacing: 0 }}>
            <thead className="bg-[#F7F7F7]">
              <tr>
                <th className={th}>Requested by</th>
                <th className={th}>Email</th>
                <th className={th}>Project Name</th>
                <th className={th}>
                  <div className="flex items-center gap-1">
                    <span>Date requested</span>
                    <button
                      type="button"
                      onClick={toggleDateSort}
                      className="inline-flex items-center rounded p-1 cursor-pointer hover:bg-neutral-95 focus:outline-none focus:ring-2 focus:ring-orange-300"
                      aria-label="Sort by date requested"
                      title="Sort by date requested"
                    >
                      <span className="material-symbols-rounded text-text-faint" style={{ fontSize: 18 }}>
                        {sortDir === "asc" ? "arrow_drop_up" : "arrow_drop_down"}
                      </span>
                    </button>
                  </div>
                </th>
                <th className={th}>Action</th>
              </tr>
            </thead>

            <tbody>
              {sorted.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-sm text-text-faint">
                    No pending requests.
                  </td>
                </tr>
              ) : (
                sorted.map((r, index) => (
                  <tr
                    key={r.id}
                    className={`h-15 ${
                      index % 2 === 0 ? "bg-white" : "bg-neutral-98"
                    }`}
                  >
                    <td className={td}>{r.requestedBy}</td>
                    <td className={td}>{r.email}</td>
                    <td className={td}>{r.projectName}</td>
                    <td className={td}>{formatDate(r.dateRequested)}</td>
                    <td className={td}>
                      <button
                        className="text-primary hover:opacity-90 cursor-pointer text-sm font-medium"
                        onClick={() => openModal(r)}
                      >
                        Review request
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}


type AccessLevel = "View" | "Edit" | "No access";
type StageName = "Business case" | "Design" | "Construction" | "N/A";

type MemberAssignment = {
  stage: StageName;
  access: AccessLevel;
};

type ProjectMember = {
  id: string;
  name: string;
  email: string;
  assignments: MemberAssignment[];
};

type ProjectRow = {
  id: string;
  name: string;
  program: string;
  category: string;
  users: number;
  dateCreated: string;
  members: ProjectMember[];
};

function roleToAssignments(roleName: string): MemberAssignment[] {
  const access: AccessLevel = roleName === "PROJECT_EDITOR" ? "Edit" : "View";
  return [
    { stage: "Business case", access },
    { stage: "Design", access },
    { stage: "Construction", access },
  ];
}

function ManageProjectsPanel() {
  const { success } = useToast();
  const [q, setQ] = useState("");
  const debouncedQ = useDebounce(q, 300);
  const [sortBy, setSortBy] = useState<"dateCreated" | "name">("dateCreated");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [panelLoading, setPanelLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      http.get("/api/me/projects"),
      userRolesService.fetchEnriched({ scope_type: "PROJECT", limit: 1000 }),
    ])
      .then(([projRes, roles]: [any, UserRoleEnriched[]]) => {
        if (cancelled) return;
        const apiProjects: any[] = projRes.data ?? [];
        const rolesByProject: Record<string, UserRoleEnriched[]> = {};
        for (const ur of roles) {
          if (!ur.scope_id) continue;
          if (!rolesByProject[ur.scope_id]) rolesByProject[ur.scope_id] = [];
          rolesByProject[ur.scope_id].push(ur);
        }
        const categoryMap: Record<string, string> = {
          SMALL: "Small",
          LARGE: "Large",
          RECURRING: "Recurring",
        };
        const rows: ProjectRow[] = apiProjects.map((p: any) => {
          const members = (rolesByProject[p.id] ?? [])
            .filter((ur) => ["PROJECT_EDITOR", "PROJECT_VIEWER"].includes(ur.role_name))
            .map((ur) => ({
              id: ur.user_id,
              name: ur.user_display_name || ur.user_email,
              email: ur.user_email,
              assignments: roleToAssignments(ur.role_name),
            }));
          return {
            id: p.id,
            name: p.project_name,
            program: p.program_name ?? "",
            category: categoryMap[p.project_class ?? ""] ?? p.project_class ?? "-",
            users: members.length,
            dateCreated: p.created_on ? String(p.created_on).slice(0, 10) : "",
            members,
          };
        });
        setProjects(rows);
      })
      .catch(() => {
        if (!cancelled) setProjects([]);
      })
      .finally(() => {
        if (!cancelled) setPanelLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const items = useMemo(() => {
    const needle = debouncedQ.trim().toLowerCase();
    const filtered = !needle
      ? projects
      : projects.filter((p) => `${p.name} ${p.program}`.toLowerCase().includes(needle));

    const sorted = [...filtered].sort((a, b) => {
      let cmp = 0;
      if (sortBy === "dateCreated") {
        const dateA = new Date(a.dateCreated).getTime();
        const dateB = new Date(b.dateCreated).getTime();
        cmp = dateA - dateB;
      } else {
        cmp = (a.name || "").localeCompare(b.name || "");
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return sorted;
  }, [projects, debouncedQ, sortBy, sortDir]);

  const [accessOpen, setAccessOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<ProjectRow | null>(null);

  const [editingMember, setEditingMember] = useState<ProjectMember | null>(null);

  const [memberToRemove, setMemberToRemove] = useState<ProjectMember | null>(null);

  const openAccessModal = (p: ProjectRow) => {
    setSelectedProject(p);
    setAccessOpen(true);
  };
  const closeAccessModal = () => {
    setAccessOpen(false);
  };

  const openEditMember = (m: ProjectMember) => setEditingMember(m);
  const closeEditMember = () => setEditingMember(null);

  const askRemoveMember = (m: ProjectMember) => setMemberToRemove(m);
  const cancelRemoveMember = () => setMemberToRemove(null);

  const confirmRemoveMember = () => {
    if (!selectedProject || !memberToRemove) return;

    const projId = selectedProject.id;
    const memberId = memberToRemove.id;

    setProjects((prev) =>
      prev.map((proj) => {
        if (proj.id !== projId) return proj;
        const newMembers = proj.members.filter((m) => m.id !== memberId);
        return {
          ...proj,
          members: newMembers,
          users: newMembers.length,
        };
      })
    );

    const removedName = memberToRemove.name;
    const projectName = selectedProject.name;
    setMemberToRemove(null);
    success(`${removedName} removed from ${projectName}`);
  };

  function saveMemberAssignments(memberId: string, nextAssignments: MemberAssignment[]) {
    if (!selectedProject) return;

    setSelectedProject((prev) => {
      if (!prev) return prev!;
      return {
        ...prev,
        members: prev.members.map((m) =>
          m.id === memberId ? { ...m, assignments: nextAssignments } : m
        ),
      };
    });

    closeEditMember();
  }

  const toggleDateSort = () => {
    if (sortBy === "dateCreated") {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy("dateCreated");
      setSortDir("desc");
    }
  };

 return (
  <section className="overflow-hidden rounded-[var(--radius-3)] bg-white">
    <div className="px-6 py-5">
      <h3 className="text-2xl font-light text-text-dark">
        Projects ({panelLoading ? "…" : items.length})
      </h3>
    </div>

    {!panelLoading && projects.length > 0 && (
      <div className="px-6 pt-4 mb-6">
        <SearchInput
          value={q}
          onChange={setQ}
          placeholder="Search by project or program name"
          className="w-98"
        />
      </div>
    )}

    <div
      className="max-h-[70vh] overflow-y-auto scroll-styled no-scroll-buttons"
      // style={{ maxHeight: 560, minHeight: 220 }}
    >
   
      {panelLoading ? (
        <div className="flex items-center justify-center h-[220px]">
          <span className="text-text-faint text-sm">
            Loading projects...
          </span>
        </div>

      
      ) : items.length === 0 && !debouncedQ ? (
        <div className="flex items-center justify-center h-[220px]">
          <span className="text-text-faint text-sm">
            No projects yet
          </span>
        </div>

    
      ) : items.length === 0 && debouncedQ ? (
        <div className="flex items-center justify-center h-[220px]">
          <span className="text-text-faint text-sm">
            No projects match your search
          </span>
        </div>

      
      ) : (
       <table
  className="min-w-full border-separate text-xs"
  style={{ borderSpacing: 0 }}
>
  <thead className="bg-[#F7F7F7] text-text-base">
    <tr>
      <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide border-b border-neutral-200">
        PROJECT NAME
      </th>

      <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide border-b border-neutral-200">
        PROJECT CATEGORY
      </th>

      <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide border-b border-neutral-200">
        NUMBER OF USERS
      </th>

      <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide border-b border-neutral-200">
        <div className="flex items-center gap-1">
          <span>DATE CREATED</span>
          <button
            type="button"
            onClick={toggleDateSort}
            className="inline-flex items-center cursor-pointer rounded p-1 hover:bg-neutral-95"
          >
            <span
              className="material-symbols-rounded text-text-faint"
              style={{ fontSize: 18 }}
            >
              {sortBy === "dateCreated" &&
                (sortDir === "asc"
                  ? "arrow_drop_up"
                  : "arrow_drop_down")}
            </span>
          </button>
        </div>
      </th>

      <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide border-b border-neutral-200">
        ACTION
      </th>
    </tr>
  </thead>

  <tbody>
    {items.map((p, index) => (
      <tr
        key={p.id}
        className={`h-14 ${
          index % 2 === 0 ? "bg-white" : "bg-neutral-98"
        } hover:bg-neutral-95 transition-colors`}
      >
        {/* PROJECT NAME */}
        <td className="px-5 py-3 text-sm text-text-dark">
          <div className="font-medium text-text-dark">
            {p.name}
          </div>
          {p.program && (
            <div className="text-xs text-text-faint mt-0.5">
              {p.program}
            </div>
          )}
        </td>

        {/* CATEGORY */}
        <td className="px-5 py-3 text-sm text-text-table-cell">
          {p.category}
        </td>

        {/* USERS */}
        <td className="px-5 py-3 text-sm text-text-table-cell">
          {p.users}
        </td>

        {/* DATE */}
        <td className="px-5 py-3 text-sm text-text-table-cell">
          {formatDate(p.dateCreated)}
        </td>

        {/* ACTION */}
        <td className="px-5 py-3 text-sm">
          <button
            onClick={() => openAccessModal(p)}
            className="text-primary font-medium cursor-pointer hover:opacity-90"
          >
            Manage access
          </button>
        </td>
      </tr>
    ))}
  </tbody>
</table>
      )}
    </div>

    
    <ManageAccessModal
      open={accessOpen}
      project={selectedProject}
      onClose={closeAccessModal}
      onEditMember={openEditMember}
      onRemoveMember={askRemoveMember}
    />

    <EditMemberAccessModal
      open={!!editingMember}
      member={editingMember}
      project={selectedProject}
      onClose={closeEditMember}
      onSave={saveMemberAssignments}
    />

    <RemoveUserConfirmModal
      open={!!memberToRemove}
      member={memberToRemove}
      project={selectedProject}
      onCancel={cancelRemoveMember}
      onConfirm={confirmRemoveMember}
    />
  </section>
);
}

function ManageAccessModal({
  open,
  project,
  onClose,
  onEditMember,
  onRemoveMember,
}: {
  open: boolean;
  project: ProjectRow | null;
  onClose: () => void;
  onEditMember: (m: ProjectMember) => void;
  onRemoveMember: (m: ProjectMember) => void;
}) {
  if (!open || !project) return null;

  const groups = project.members.map((member) => {
    const rows = member.assignments.map((a, idx) => ({
      key: `${member.id}-${a.stage}-${idx}`,
      member,
      assignment: a,
      isFirst: idx === 0,
      isLast: idx === member.assignments.length - 1,
      rowSpan: member.assignments.length,
    }));

    if (rows.length === 0) {
      return [
        {
          key: `${member.id}--empty`,
          member,
          assignment: { stage: "N/A", access: "View" } as unknown as MemberAssignment,
          isFirst: true,
          isLast: true,
          rowSpan: 1,
        },
      ];
    }
    return rows;
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="manage-access-title"
    >
      <div className="my-8 w-[960px] max-w-[95vw] rounded-md bg-white shadow-xl">
        <div className="px-6 pt-6">
          <h3 id="manage-access-title" className="mb-1 text-[22px] font-normal text-text-dark">
            {project.name}
          </h3>
          {project.program && (
            <p className="mb-6 text-sm text-text-faint">{project.program}</p>
          )}
          <h4 className="mb-3 text-xl font-normal text-heading">Manage access</h4>
        </div>
        <div className="px-6 pb-6">
          <div className="max-h-[360px] ">
            <div className="max-h-[70vh] overflow-y-auto scroll-styled no-scroll-buttons">
              <table className="w-full border-collapse" style={{ borderSpacing: 0 }}>
                <thead className="sticky top-0 z-10 bg-neutral-90">
                  <tr className="border-b-1 border-neutral">
                    <th
                      className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-base border-r-2 border-neutral"
                      style={{ position: "sticky", top: 0 }}
                    >
                      Name
                    </th>
                    <th
                      className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-base border-r-2 border-neutral"
                      style={{ position: "sticky", top: 0 }}
                    >
                      Project stage
                    </th>
                    <th
                      className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-base border-r-2 border-neutral"
                      style={{ position: "sticky", top: 0 }}
                    >
                      Access
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-base">
                      Actions
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {groups.length === 0 ? (
                    <tr>
                      <td
                        colSpan={4}
                        className="px-6 py-6 text-sm text-text-base border-b-1 border-neutral"
                      >
                        No members yet.
                      </td>
                    </tr>
                  ) : (
                    groups.flatMap((rows) =>
                      rows.map(({ key, member, assignment, isFirst, rowSpan }) => {
                        return (
                          <tr key={key} className="align-top">
                            {isFirst && (
                              <td
                                className="px-5 py-4 align-top text-left border-r-1 border-neutral"
                                rowSpan={rowSpan}
                                style={{
                                  borderTop: "1px solid rgb(232, 232, 232)",
                                  borderBottom: "1px solid rgb(232, 232, 232)",
                                }}
                              >
                                <div className="flex flex-col gap-1">
                                  <div className="text-[15px] text-text-dark">{member.name}</div>
                                  <div className="text-xs text-text-faint">{member.email}</div>
                                </div>
                              </td>
                            )}

                            <td className="px-5 py-4 text-text-table-cell border-r-1 border-b-1 border-neutral">
                              {assignment.stage}
                            </td>

                            <td className="px-5 py-4 text-text-table-cell border-r-1 border-b-1 border-neutral">
                              {assignment.access}
                            </td>

                            {isFirst && (
                              <td
                                rowSpan={rowSpan}
                                className="px-5 py-0 border-b-1 border-neutral"
                                style={{
                                  borderTop: "1px solid rgb(232, 232, 232)",
                                  borderBottom: "1px solid rgb(232, 232, 232)",
                                  verticalAlign: "middle",
                                }}
                              >
                                <div className="h-full min-h-full flex items-center justify-center gap-5 py-4">
                                  <button
                                    className="inline-flex items-center cursor-pointer gap-1 text-sm text-primary"
                                    onClick={() => onEditMember(member)}
                                  >
                                    <img src={editIconUrl} alt="Edit" className="w-4 h-4" aria-hidden />
                                    <span className="font-medium">Edit</span>
                                  </button>

                                  <button
                                    className="inline-flex items-center cursor-pointer gap-1 text-sm"
                                    onClick={() => onRemoveMember(member)}
                                  >
                                    <span
                                      className="material-symbols-rounded text-[18px] text-text-table-cell"
                                      aria-hidden
                                      style={{ fontVariationSettings: "'FILL' 1" }}
                                    >
                                      close
                                    </span>
                                    <span className="font-medium">Remove</span>
                                  </button>
                                </div>
                              </td>
                            )}
                          </tr>
                        );
                      })
                    )
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={onClose}
              className=" px-4 py-2 rounded-[var(--radius-3)] text-sm font-medium cursor-pointer text-text-table-cell bg-white border border-text-table-cell hover:bg-neutral-95"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function EditMemberAccessModal({
  open,
  member,
  project,
  onClose,
  onSave,
}: {
  open: boolean;
  member: ProjectMember | null;
  project: ProjectRow | null;
  onClose: () => void;
  onSave: (memberId: string, nextAssignments: MemberAssignment[]) => void;
}) {
  if (!open || !member || !project) return null;

  const ORDER: StageName[] = ["Business case", "Design", "Construction"];
  const foundStages = Array.from(
    new Set(project.members.flatMap((m) => m.assignments.map((a) => a.stage)))
  ) as StageName[];
  const stages = [
    ...ORDER.filter((s) => foundStages.includes(s)),
    ...foundStages.filter((s) => !ORDER.includes(s)),
  ];

  const [form, setForm] = useState<Record<string, AccessLevel | "">>({});
  const [initial, setInitial] = useState<Record<string, AccessLevel | "">>({});
  const [showDiscard, setShowDiscard] = useState(false);

  useEffect(() => {
    const init: Record<string, AccessLevel | ""> = {};
    stages.forEach((s) => {
      const match = member.assignments.find((a) => a.stage === s);
      init[s] = match ? match.access : "";
    });
    setInitial(init);
    setForm(init);
    setShowDiscard(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [member, stages.join("|")]);

  const setStageAccess = (stage: string, access: AccessLevel) =>
    setForm((prev) => ({ ...prev, [stage]: access }));

  const isDirty = useMemo(() => {
    return Object.keys(initial).some((k) => initial[k] !== form[k]);
  }, [initial, form]);

  const handleCancel = () => {
    if (isDirty) {
      setShowDiscard(true);
    } else {
      onClose();
    }
  };

  const handleDiscard = () => {
    setForm(initial);
    setShowDiscard(false);
    onClose();
  };

  const handleSave = () => {
    const next: MemberAssignment[] = stages
      .filter((s) => form[s] === "View" || form[s] === "Edit" || form[s] === "No access")
      .map((s) => ({ stage: s as StageName, access: form[s]! as AccessLevel }));
    onSave(member.id, next);
    onClose();
  };

  return (
    <>
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30">
        <div className="w-150 max-w-[95vw] rounded-md bg-white p-6 shadow-xl">
          <h3 className="text-2xl font-normal text-text-dark mb-6">
            Edit access for {member.name}
          </h3>

          <div className="mt-4">
            <div className=" font-medium mb-1 text-text-dark text-base">Project stage access</div>
            <div className="text-text-faint text-sm mb-4">
              Select the access type required for each project stage
            </div>

            <div className="overflow-hidden ">
              <table className="w-full text-sm">
                <thead className="border-b border-light">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-xs text-text-dark">
                      PROJECT STAGES
                    </th>
                    <th className="px-4 py-2 text-left font-medium text-xs text-text-dark">VIEW</th>
                    <th className="px-4 py-2 text-left font-medium text-xs text-text-dark">EDIT</th>
                    <th className="px-4 py-2 text-left font-medium text-xs text-text-dark">
                      NO ACCESS
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {stages.map((stage) => (
                    <tr key={stage} className="border-b border-light">
                      <td className="px-4 py-3 text-text-table-cell">{stage}</td>

                      <td className="px-4 py-3">
                        <label className="inline-flex cursor-pointer">
                          <input
                            type="radio"
                            name={`stage-${stage}`}
                            checked={form[stage] === "View"}
                            onChange={() => setStageAccess(stage, "View")}
                            className="sr-only peer"
                            aria-checked={form[stage] === "View"}
                          />

                          <span
                            className={`material-symbols-rounded text-xl ${
                              form[stage] === "View" ? "text-primary" : "text-text-base"
                            }`}
                          >
                            {form[stage] === "View"
                              ? "radio_button_checked"
                              : "radio_button_unchecked"}
                          </span>
                        </label>
                      </td>

                      <td className="px-4 py-3">
                        <label className="inline-flex items-center  cursor-pointer">
                          <input
                            type="radio"
                            name={`stage-${stage}`}
                            checked={form[stage] === "Edit"}
                            onChange={() => setStageAccess(stage, "Edit")}
                            className="sr-only peer"
                            aria-checked={form[stage] === "Edit"}
                          />

                          <span
                            className={`material-symbols-rounded text-xl ${
                              form[stage] === "Edit" ? "text-primary" : "text-text-base"
                            }`}
                          >
                            {form[stage] === "Edit"
                              ? "radio_button_checked"
                              : "radio_button_unchecked"}
                          </span>
                        </label>
                      </td>

                      <td className="px-4 py-3">
                        <label className="inline-flex cursor-pointer">
                          <input
                            type="radio"
                            name={`stage-${stage}`}
                            checked={form[stage] === "No access"}
                            onChange={() => setStageAccess(stage, "No access")}
                            className="sr-only peer"
                            aria-checked={form[stage] === "No access"}
                          />

                          <span
                            className={`material-symbols-rounded text-xl ${
                              form[stage] === "No access" ? "text-primary" : "text-text-base"
                            }`}
                          >
                            {form[stage] === "No access"
                              ? "radio_button_checked"
                              : "radio_button_unchecked"}
                          </span>
                        </label>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={handleCancel}
                className="text-text-table-cell font-medium cursor-pointer bg-white px-4 py-2 text-sm"
              >
                Cancel
              </button>

              <button
                onClick={handleSave}
                className="rounded-[var(--radius-3)] px-4.5 py-2.5 text-sm cursor-pointer font-medium text-white bg-primary"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      </div>

      {showDiscard && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/30">
          <div className="w-[480px] max-w-[95vw] rounded-md bg-white p-6 shadow-xl">
            <h3 className="text-2xl font-light mb-4">Discard changes</h3>
            <p className="text-text-base mb-6">
              You have unsaved changes to <span className="font-medium">{member.name}’s</span>{" "}
              access. Closing will discard these changes.
            </p>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDiscard(false)}
                className="rounded border border-border-input cursor-pointer bg-white px-4 py-2 text-sm"
              >
                Keep editing
              </button>

              <button
                onClick={handleDiscard}
                className="rounded bg-orange-700 px-4 py-2 cursor-pointer text-sm font-medium text-white"
              >
                Discard changes
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function RemoveUserConfirmModal({
  open,
  member,
  project,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  member: ProjectMember | null;
  project: ProjectRow | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!open || !member || !project) return null;

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-black/30"
      role="dialog"
      aria-modal="true"
      aria-labelledby="remove-user-title"
    >
      <div className="w-100 max-w-[95vw] rounded-md bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-start gap-3">
          <img
            src={alertIconUrl}
            alt=""
            width={25}
            height={25}
            aria-hidden="true"
            className="mt-1"
          />
          <h3 id="remove-user-title" className="text-2xl font-light text-text-dark">
            Remove user from project
          </h3>
        </div>

        <p className="text-text-base mb-12">
          You’re about to remove <span className="font-medium">{member.name}</span> from{" "}
          <span className="font-medium">{project.name}</span>. All access permissions will be
          revoked.
        </p>

        <div className="flex justify-end gap-3">
          <button onClick={onCancel} className="text-text-table-cell px-4 py-2 text-sm font-medium">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded bg-danger px-4 py-2 text-sm font-medium text-white hover:bg-red-800"
          >
            Remove user
          </button>
        </div>
      </div>
    </div>
  );
}


function ProjectAdminGroupList({
  projects,
  onAddAdmin,
  onRemoveAdmin,
  disableAddAdmin,
  removeAdminLoading,
}: {
  projects: { id: string; name: string; admins: UserRoleEnriched[] }[];
  onAddAdmin: (projectId: string, projectName: string) => void;
  onRemoveAdmin: (projectId: string, userId: string) => void;
  disableAddAdmin: boolean;
  removeAdminLoading: Record<string, boolean>;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [removeConfirm, setRemoveConfirm] = useState<{
    projectId: string;
    userId: string;
    userName: string;
    projectName: string;
  } | null>(null);

  const handleRemoveClick = (
    projectId: string,
    userId: string,
    userName: string,
    projectName: string,
    adminCount: number
  ) => {
    if (adminCount === 1) return;
    setRemoveConfirm({ projectId, userId, userName, projectName });
  };

  const confirmRemove = () => {
    if (removeConfirm) {
      onRemoveAdmin(removeConfirm.projectId, removeConfirm.userId);
      setRemoveConfirm(null);
    }
  };

  return (
    <>
      <ul>
        {projects.map((project) => {
          const isOpen = expanded[project.id];
          const adminCount = project.admins.length;

          return (
            <li key={project.id}>
              <div className="flex justify-between px-6 py-4">
                <button
                  onClick={() =>
                    setExpanded((p) => ({
                      ...p,
                      [project.id]: !p[project.id],
                    }))
                  }
                  className="flex-1 text-left font-medium flex items-center gap-3"
                >
                  <span
                    className={`material-symbols-rounded text-text-base transition-transform ${
                      isOpen ? "rotate-180" : ""
                    }`}
                    style={{ fontSize: 20 }}
                  >
                    expand_more
                  </span>
                  {project.name} ({adminCount})
                </button>

                <button
                  onClick={() => onAddAdmin(project.id, project.name)}
                  className={`text-sm ${
                    disableAddAdmin
                      ? "text-gray-300 cursor-not-allowed"
                      : "text-primary hover:opacity-80"
                  }`}
                  disabled={disableAddAdmin}
                >
                  + Add Admin
                </button>
              </div>

              {isOpen && (
                <ul className="bg-neutral-98">
                  {adminCount === 0 ? (
                    <li className="px-8 py-3 text-sm text-text-faint">
                      No project administrators assigned.
                    </li>
                  ) : (
                    project.admins.map((m) => (
                      <li
                        key={m.user_id}
                        className="flex justify-between px-8 py-3 items-center"
                      >
                        <div>
                          <div className="text-sm font-medium">
                            {m.user_display_name || m.user_email}
                          </div>
                          {m.user_display_name && (
                            <div className="text-xs text-text-faint">
                              {m.user_email}
                            </div>
                          )}
                        </div>

                        <button
                          onClick={() =>
                            handleRemoveClick(
                              project.id,
                              m.user_id,
                              m.user_display_name || m.user_email,
                              project.name,
                              adminCount
                            )
                          }
                          disabled={
                            adminCount === 1 ||
                            removeAdminLoading[`${project.id}-${m.user_id}`]
                          }
                          className={`text-danger hover:text-danger ${
                            adminCount === 1
                              ? "opacity-40 cursor-not-allowed"
                              : ""
                          }`}
                          title={
                            adminCount === 1
                              ? "Cannot remove the only project admin"
                              : "Remove admin"
                          }
                        >
                          <span className="material-symbols-rounded">
                            delete
                          </span>
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              )}
            </li>
          );
        })}
      </ul>

      {removeConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30">
          <div className="w-150 max-w-[95vw] rounded-md bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start gap-3">
              <img
                src={alertIconUrl}
                alt=""
                width={28}
                height={28}
                aria-hidden="true"
                className="mt-1"
              />
              <h3 className="text-xl font-light text-text-dark">
                Remove project administrator
              </h3>
            </div>

            <p className="text-text-base mb-6">
              You're about to remove{" "}
              <span className="font-medium">{removeConfirm.userName}</span> as
              the project administrator of{" "}
              <span className="font-medium italic">
                {removeConfirm.projectName}
              </span>
              . Once removed, they will no longer be able to review project
              data submissions and manage access for this project.
            </p>
            <p>Do you want to proceed?</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setRemoveConfirm(null)}
                className="text-text-table-cell px-4 py-2 text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={confirmRemove}
                className="rounded bg-danger px-4 py-2 text-sm font-medium text-white hover:bg-red-800"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ProjectAdminsView({
  projectAdminsLoading,
  projectAdminProjects,
  onBack,
  onAddAdmin,
  onRemoveAdmin,
  assignProjectId,
  assignProjectName,
  isAssignModalOpen,
  orgUsers,
  onAssign,
  onCloseAssignModal,
}: {
  projectAdminsLoading: boolean;
  projectAdminProjects: { id: string; name: string; admins: UserRoleEnriched[] }[];
  onBack: () => void;
  onAddAdmin: (projectId: string, projectName: string) => void;
  onRemoveAdmin: (projectId: string, userId: string) => void;
  assignProjectId: string | null;
  assignProjectName: string | null;
  isAssignModalOpen: boolean;
  orgUsers: DisplayOrgUser[];
  onAssign: (userId: string) => Promise<void>;
  onCloseAssignModal: () => void;
}) {
  const [removeAdminLoading, setRemoveAdminLoading] = useState<Record<string, boolean>>({});

  const handleRemoveAdmin = async (projectId: string, userId: string) => {
    const key = `${projectId}-${userId}`;
    setRemoveAdminLoading(prev => ({ ...prev, [key]: true }));
    await onRemoveAdmin(projectId, userId);
    setRemoveAdminLoading(prev => ({ ...prev, [key]: false }));
  };

  return (
    <>
      <BackButton onClick={onBack} />

      <section className="mt-8 bg-white">
        <div className=" px-6 py-5">
          <h3 className="text-2xl font-light">
            All projects ({projectAdminProjects.length})
          </h3>
        </div>

        {projectAdminsLoading ? (
          <div className="px-6 py-8 text-sm text-text-faint">Loading…</div>
        ) : projectAdminProjects.length === 0 ? (
          <div className="px-6 py-8 text-sm text-text-faint">
            No projects found.
          </div>
        ) : (
          <>
            <ProjectAdminGroupList
              projects={projectAdminProjects}
              onAddAdmin={onAddAdmin}
              onRemoveAdmin={handleRemoveAdmin}
              disableAddAdmin={isAssignModalOpen}
              removeAdminLoading={removeAdminLoading}
            />

            {assignProjectId && assignProjectName && (
              <AssignProjectAdminModal
                projectName={assignProjectName}
                users={orgUsers}
                onClose={onCloseAssignModal}
                onAssign={onAssign}
              />
            )}
          </>
        )}
      </section>
    </>
  );
}


function AssignProjectAdminModal({
  projectName,
  users,
  onClose,
  onAssign,
}: {
  projectName: string;
  users: { id: string; email: string; name?: string; display_name?: string; has_org_admin_role?: boolean }[];
  onClose: () => void;
  onAssign: (userId: string) => Promise<void>;
}) {
  const [query, setQuery] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  
  const selectedQueryRef = useRef<string>("");

  const filteredUsers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return users.filter(
      (u) =>
        (u.email.toLowerCase().includes(q) ||
          u.name?.toLowerCase().includes(q) ||
          u.display_name?.toLowerCase().includes(q))
    );
  }, [query, users]);

  const handleSelectUser = (userId: string) => {
    setSelectedUserId(userId);
    selectedQueryRef.current = query; 
    setAssignError(null);
  };

  const handleAssign = async () => {
    if (!selectedUserId) return;

    setLoading(true);
    setAssignError(null);

    try {
      await onAssign(selectedUserId);
      onClose(); 
    } catch (err: any) {
      setAssignError(
        err?.message || "Failed to assign administrator. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-150 max-w-[95vw] rounded-[var(--radius-3)] bg-white p-6 shadow-xl">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-lg font-medium text-text-dark">
              Assign a project administrator
            </h2>
            <p className="text-sm text-text-base mt-1 mb-2">{projectName}</p>
          </div>
          <button
            onClick={onClose}
            className="text-text-base hover:text-text-base"
          >
            <span className="material-symbols-rounded">close</span>
          </button>
        </div>

        {/* Search */}
        <div className="mt-4">
          <label className="text-sm font-medium text-text-base">
            Search by name or email
          </label>

          <div className="relative mt-1">
            <span className="material-symbols-rounded absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xl">
              search
            </span>
            <input
              value={query}
              onChange={(e) => {
                const newQuery = e.target.value;
                setQuery(newQuery);

                if (
                  selectedUserId &&
                  newQuery !== selectedQueryRef.current
                ) {
                  setSelectedUserId(null);
                }

                setAssignError(null);
              }}
              className="w-full rounded-md border border-border-input pl-10 pr-10 py-2 text-sm"
            />
            {query.trim() && (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setSelectedUserId(null);
                  selectedQueryRef.current = "";
                  setAssignError(null);
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-text-base"
                aria-label="Clear search"
              >
                <span className="material-symbols-rounded">close</span>
              </button>
            )}
          </div>

          {query.trim() && (
            <div className="mt-2 max-h-48 overflow-auto rounded-[var(--radius-3)] border border-border bg-white">
              {filteredUsers.length === 0 ? (
                <div className="px-4 py-3 text-sm text-text-faint">
                  No users found matching "{query}"
                </div>
              ) : (
                filteredUsers.map((u) => (
                  <div
                    key={`${u.id}-${u.email}`} // ✅ unique key
                    onClick={() => handleSelectUser(u.id)}
                    className={`cursor-pointer px-4 py-3 hover:bg-neutral-98 transition-colors ${
                      selectedUserId === u.id
                        ? "bg-primary-weak border-l-4 border-primary"
                        : ""
                    }`}
                  >
                    <div className="text-sm font-medium text-text-dark">
                      {u.display_name || u.name || u.email}
                    </div>
                    <div className="text-xs text-text-faint mt-0.5">
                      {u.email}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* {!query.trim() && (
            <div className="mt-2 rounded-md border border-border bg-neutral-98 px-4 py-3 text-sm text-text-faint">
              Start typing to search for users in your organisation
            </div>
          )} */}

          {assignError && (
            <div className="mt-2 text-sm text-danger bg-red-50 rounded-md px-3 py-2">
              {assignError}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-3">
           <button
                 onClick={onClose}
                className="text-text-table-cell font-medium bg-white px-4 py-2 text-sm"
              >
                Cancel
              </button>
          <button
            disabled={!selectedUserId || loading}
            onClick={handleAssign}
            className={`px-4 py-2 text-sm font-medium text-white rounded-md ${
              !selectedUserId || loading
                ? "bg-orange-300 cursor-not-allowed"
                : "bg-primary hover:bg-primary-dark"
            }`}
          >
            {loading ? "Assigning..." : "Assign as project administrator"}
          </button>
        </div>
      </div>
    </div>
  );
}


function OrgUsersView({
  users,
  search,
  setSearch,
  sortDir,
  toggleSort,
  onBack,
  onRefreshUsers,
  onMakeOrgAdmin,
  onRemoveOrgAdmin,
  currentUserId,
}: {
  users: DisplayOrgUser[];
  search: string;
  setSearch: (v: string) => void;
  sortDir: "asc" | "desc";
  toggleSort: () => void;
  onBack: () => void;
  onRefreshUsers: () => Promise<void>;
  onMakeOrgAdmin?: (userId: string, userName: string) => Promise<void>;
  onRemoveOrgAdmin?: (userRoleId: string, userName: string) => Promise<void>;
  currentUserId?: string;
}) {
  const { success, error } = useToast();

  const [expandedUser, setExpandedUser] = useState<string | null>(null);
  const [removeConfirm, setRemoveConfirm] = useState<{
    userId: string;
    userName: string;
  } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [makeAdminConfirm, setMakeAdminConfirm] = useState<{ userId: string; userName: string } | null>(null);
  const [makingAdmin, setMakingAdmin] = useState(false);
  const [removeAdminConfirm, setRemoveAdminConfirm] = useState<{ userRoleId: string; userName: string } | null>(null);
  const [removingAdmin, setRemovingAdmin] = useState(false);

  const toggleUser = (userId: string) =>
    setExpandedUser(prev => (prev === userId ? null : userId));

  const groupRolesByProject = (user: any) => {
    const grouped: Record<string, any[]> = {};
    (user.project_roles || []).forEach((role: any) => {
      const key = role.project_name || "Unknown Project";
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(role);
    });
    return Object.entries(grouped);
  };

  const confirmRemoveUser = async () => {
    if (!removeConfirm) return;

    try {
      setDeleting(true);

      await orgAdminService.deleteOrgUser(removeConfirm.userId);

      success(`${removeConfirm.userName} removed from organisation`);
      setExpandedUser(null);

      // ✅ refresh list from server
      await onRefreshUsers();
    } catch (e) {
      console.error(e);
      error("Failed to remove user");
    } finally {
      setDeleting(false);
      setRemoveConfirm(null);
    }
  };

  return (
    <>
      <BackButton onClick={onBack} />

      <section className="bg-white">
        {/* Header */}
        <div className="px-6 py-4">
          <h3 className="text-xl font-light text-text-dark">
            Organisation users ({users.length})
          </h3>
        </div>

        {/* Search */}
        <div className="px-6 mb-4">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or email"
            className="w-full max-w-96 px-3 py-2 text-sm border rounded-[var(--radius-3)]"
          />
        </div>

        {/* Users list (scrollable, reduced height) */}
        <div
          className="px-4 overflow-y-auto"
          style={{ height: 340 }}
        >
          {/* Column header */}
          <div className="flex px-2 py-2 text-xs uppercase text-text-faint">
            <div className="flex-1 flex items-center gap-1">
              Name
              <button onClick={toggleSort}>
                <span className="material-symbols-rounded">
                  {sortDir === "asc" ? "arrow_drop_up" : "arrow_drop_down"}
                </span>
              </button>
            </div>
            <div className="flex-1 hidden sm:block">Email</div>
            <div className="w-10" />
          </div>

          {users.map((u) => {
            const isOpen = expandedUser === u.id;
            const groupedRoles = groupRolesByProject(u);
            const hasRoles = groupedRoles.length > 0;

            return (
              <div key={u.id} className="mb-1">
                {/* User row */}
                <div
                  className="flex items-center px-2 py-3 rounded cursor-pointer hover:bg-neutral-98"
                  onClick={() => toggleUser(u.id)}
                >
                  <div className="flex-1 flex items-center gap-2">
                    <span className="material-symbols-rounded text-text-faint">
                      {isOpen ? "expand_more" : "chevron_right"}
                    </span>
                    <span className="text-sm truncate">{u.name}</span>
                  </div>

                  <div className="flex-1 hidden sm:block text-sm text-text-base truncate">
                    {u.email}
                  </div>

                  
                  {onMakeOrgAdmin && !u.has_org_admin_role && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMakeAdminConfirm({ userId: u.id, userName: u.name });
                      }}
                      className="text-primary hover:opacity-75 mr-2"
                      title="Make Org Admin"
                    >
                      <span className="material-symbols-rounded text-[18px]">admin_panel_settings</span>
                    </button>
                  )}
                  {onRemoveOrgAdmin && u.has_org_admin_role && u.org_admin_user_role_id && u.id !== currentUserId && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setRemoveAdminConfirm({ userRoleId: u.org_admin_user_role_id!, userName: u.name });
                      }}
                      className="text-warning hover:opacity-75 mr-2"
                      title="Remove Org Admin role"
                    >
                      <span className="material-symbols-rounded text-[18px]">admin_panel_settings</span>
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setRemoveConfirm({
                        userId: u.id,
                        userName: u.name,
                      });
                    }}
                    className="text-danger hover:text-danger"
                    title="Remove user from organisation"
                  >
                    <span className="material-symbols-rounded text-[18px]">
                      delete
                    </span>
                  </button>
                </div>

                {/* Accordion */}
                {isOpen && (
                  <div className="ml-8 mb-3">
                    {!hasRoles ? (
                      <div className="text-sm text-text-faint">
                        No project assignments
                      </div>
                    ) : (
                      <div className="max-h-40 overflow-y-auto space-y-3">
                        {groupedRoles.map(([projectName, roles]) => (
                          <div key={projectName}>
                            <div className="text-sm font-medium text-text-base mb-1">
                              {projectName}
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {roles.map((r: any) => (
                                <span
                                  key={r.user_role_id}
                                  className={`text-xs px-2 py-1 rounded ${
                                    r.role_name === "PROJECT_ADMIN"
                                      ? "bg-purple-100 text-purple-800"
                                      : r.role_name === "PROJECT_EDITOR"
                                      ? "bg-blue-100 text-blue-800"
                                      : "bg-neutral-95 text-gray-800"
                                  }`}
                                >
                                  {formatRoleLabel(r.role_name)}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
      {removeConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-96 rounded-md bg-white p-6 shadow-xl">
            <h3 className="text-lg font-medium mb-4">
              Remove user
            </h3>

            <p className="text-sm text-text-base mb-6">
              Are you sure you want to remove{" "}
              <span className="font-medium">
                {removeConfirm.userName}
              </span>{" "}
              from the organisation? This will remove all access.
            </p>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setRemoveConfirm(null)}
                className="text-sm px-4 py-2"
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                onClick={confirmRemoveUser}
                disabled={deleting}
                className="rounded bg-danger px-4 py-2 text-sm font-medium text-white hover:bg-red-800 disabled:opacity-60"
              >
                {deleting ? "Removing..." : "Remove"}
              </button>
            </div>
          </div>
        </div>
      )}

      {makeAdminConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-96 rounded-md bg-white p-6 shadow-xl">
            <h3 className="text-lg font-medium mb-4">Assign as Org Admin</h3>
            <p className="text-sm text-text-base mb-6">
              Assign <span className="font-medium">{makeAdminConfirm.userName}</span> as an Org Admin?
              They will be able to manage users and projects within this organisation.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setMakeAdminConfirm(null)}
                className="text-sm px-4 py-2"
                disabled={makingAdmin}
              >
                Cancel
              </button>
              <button
                disabled={makingAdmin}
                onClick={async () => {
                  if (!onMakeOrgAdmin) return;
                  try {
                    setMakingAdmin(true);
                    await onMakeOrgAdmin(makeAdminConfirm.userId, makeAdminConfirm.userName);
                    setMakeAdminConfirm(null);
                  } catch {
                    error("Failed to assign Org Admin. Please try again.");
                  } finally {
                    setMakingAdmin(false);
                  }
                }}
                className="rounded bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
              >
                {makingAdmin ? "Assigning..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {removeAdminConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-96 rounded-md bg-white p-6 shadow-xl">
            <h3 className="text-lg font-medium mb-4">Remove Org Admin role</h3>
            <p className="text-sm text-text-base mb-6">
              Remove the Org Admin role from{" "}
              <span className="font-medium">{removeAdminConfirm.userName}</span>?
              They will retain their organisation membership but lose admin privileges.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setRemoveAdminConfirm(null)}
                className="text-sm px-4 py-2"
                disabled={removingAdmin}
              >
                Cancel
              </button>
              <button
                disabled={removingAdmin}
                onClick={async () => {
                  if (!onRemoveOrgAdmin) return;
                  try {
                    setRemovingAdmin(true);
                    await onRemoveOrgAdmin(removeAdminConfirm.userRoleId, removeAdminConfirm.userName);
                    setRemoveAdminConfirm(null);
                  } catch {
                    error("Failed to remove Org Admin role. Please try again.");
                  } finally {
                    setRemovingAdmin(false);
                  }
                }}
                className="rounded bg-danger px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
              >
                {removingAdmin ? "Removing..." : "Remove"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function OrgAdminReviewModal({
  open,
  request,
  formerror,
  onClose,
  onApprove,
  onReject,
}: {
  open: boolean;
  request: OrgAdminAccessRequest | null;
  formerror: string;
  onClose: () => void;
  onApprove: (r: OrgAdminAccessRequest) => void;
  onReject: (r: OrgAdminAccessRequest, reason: string) => void;
}) {
  const [mode, setMode] = useState<"idle" | "rejecting">("idle");
  const [reason, setReason] = useState("");
  const [showError, setShowError] = useState(false);

  useEffect(() => {
    if (open) {
      setMode("idle");
      setReason("");
      setShowError(false);
    }
  }, [open, request?.id]);

  if (!open || !request) return null;

  const approve = () => onApprove(request);
  const startReject = () => setMode("rejecting");

  const confirmReject = () => {
    if (!reason.trim()) {
      setShowError(true);
      return;
    }
    onReject(request, reason.trim());
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      role="dialog"
      aria-modal="true"
      aria-labelledby="oa-review-title"
    >
      <div className="w-149 max-w-[95vw] rounded-md bg-white p-6 shadow-xl">
        <h3 id="oa-review-title" className="text-2xl font-light text-text-dark mb-6">
          Review request for administrative access
        </h3>

        <div className="space-y-3 mb-4 text-sm">
          <div>
            <label className="mb-1 block text-xs font-medium text-text-faint">REQUESTED BY</label>
            <div className="text-text-dark mb-3">{request.requestedBy}</div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-text-faint pt-2">PROJECT</label>
            <div className="text-text-dark mb-2">{request.projectName}</div>
          </div>

          <div className="mt-4 text-sm text-text-base mb-4">
            <label className="mb-1 block text-xs font-medium text-text-faint">JUSTIFICATION</label>
            <span className="bg-info-bg block p-4 text-info-text">
              {request.justification ? request.justification : "No justification provided."}
            </span>
          </div>

          {mode === "rejecting" && (
            <div className="mt-5">
              <div className="mb-4">
                <div className="h-px bg-neutral-95"></div>
              </div>
              <label className="mb-1 block text-xs font-medium text-text-faint">
                REASON FOR REJECTION (REQUIRED)
              </label>
              <textarea
                id="reject-reason"
                className={`h-40 w-full rounded-[var(--radius-3)] border-2 px-3 py-2 text-sm outline-none ${
                  showError ? "border-danger" : "border-border-input"
                }`}
                value={reason}
                onChange={(e) => {
                  setReason(e.target.value);
                  if (showError) setShowError(false);
                }}
                rows={3}
                placeholder=""
                aria-invalid={showError ? true : undefined}
                aria-describedby={showError ? "reject-reason-error" : undefined}
              />
              {showError && (
                <div
                  role="alert"
                  aria-live="assertive"
                  className="mb-2 mt-1 flex items-center gap-1.5 text-sm text-danger"
                >
                  <img src={alertIconUrl} alt="" width={20} height={20} aria-hidden="true" />
                  <span>{formerror}</span>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-start gap-72">
          <button
            onClick={onClose}
            className="bg-white font-medium px-4 py-2 text-sm text-text-table-cell"
          >
            Cancel
          </button>

          {mode === "idle" ? (
            <div className="flex gap-3">
              <button
                onClick={startReject}
                className="rounded border border-text-table-cell font-medium bg-white px-4 py-2 text-sm text-text-table-cell"
              >
                Reject
              </button>
              <button
                onClick={approve}
                className="rounded bg-primary px-4 py-2 text-sm font-medium text-white"
              >
                Approve
              </button>
            </div>
          ) : (
            <button
              onClick={confirmReject}
              className="rounded-[var(--radius-3)] ml-11 bg-primary px-4 py-2 text-sm font-medium text-white"
            >
              Confirm rejection
            </button>
          )}
        </div>
      </div>
    </div>
  );
}


function formatDate(input: string) {
  // Handle both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS formats
  const dateMatch = input.match(/^\d{4}-\d{2}-\d{2}/);
  if (!dateMatch) return input;
  const dateStr = dateMatch[0];
  const d = new Date(dateStr + "T00:00:00");
  const day = d.getDate();
  const month = d.toLocaleString("en-GB", { month: "long" });
  const year = d.getFullYear();
  return `${day} ${month} ${year}`;
}

function formatRoleLabel(role: string): string {
  const map: Record<string, string> = {
    PROJECT_ADMIN: "Project Admin",
    PROJECT_EDITOR: "Project Editor",
    PROJECT_VIEWER: "Project Viewer",
  };
  return map[role] ?? role;
}
