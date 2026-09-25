import React, { useEffect, useMemo, useState } from "react";
import ProjectsService from "@/services/Projects.service";
import ProjectAccessService from "@/services/ProjectAccess.service";
import orgAdminService from "@/services/orgAdmin.service";
import type {
  ProjectAccess,
  ProjectAccessMember,
  ProjectStageAssignment,
  StageAccess,
} from "@/types/authorization";
import { useToast } from "@/components/common/ToastProvider";

const STAGE_LABELS: Record<string, string> = {
  BUSINESS_CASE: "Business case",
  DESIGN: "Design",
  CONSTRUCTION: "Construction",
  RECURRING: "Recurring",
};

const ACCESS_OPTIONS: Array<"VIEW" | "EDIT"> = ["VIEW", "EDIT"];

type OrgUser = {
  id: string;
  name: string;
  email: string;
  has_org_admin_role?: boolean;
};

type ProjectListItem = {
  id: string;
  project_name?: string;
  projectName?: string;
};

type ProjectDetail = {
  project_class?: string;
  stage_configs?: Array<{ stage: string; enabled: boolean }>;
};

function stageLabel(stage: StageAccess) {
  return stage.stage_label || STAGE_LABELS[stage.stage] || stage.stage;
}

function accessLabel(access: StageAccess["access"]) {
  switch (access) {
    case "ADMIN":
      return "Admin";
    case "EDIT":
      return "Edit";
    case "VIEW":
      return "View";
    default:
      return "No access";
  }
}

function StageAccessEditModal({
  open,
  member,
  stages,
  onClose,
  onSave,
  saving,
  enabledStageIds,
}: {
  open: boolean;
  member: ProjectAccessMember | null;
  stages: StageAccess[];
  onClose: () => void;
  onSave: (assignments: ProjectStageAssignment[]) => Promise<void>;
  saving: boolean;
  enabledStageIds: Set<string>;
}) {
  const [form, setForm] = useState<Record<string, "" | "VIEW" | "EDIT">>({});

  useEffect(() => {
    if (!member) {
      setForm({});
      return;
    }

    const next: Record<string, "" | "VIEW" | "EDIT"> = {};
    for (const stage of stages) {
      const existing = member.assignments.find(
        (assignment) => assignment.stage_instance_id === stage.stage_instance_id,
      );
      next[stage.stage_instance_id] =
        existing?.access === "VIEW" || existing?.access === "EDIT"
          ? existing.access
          : "";
    }
    setForm(next);
  }, [member, stages]);

  if (!open || !member) return null;

  const submit = async () => {
    const assignments = Object.entries(form)
      .filter(([, access]) => access === "VIEW" || access === "EDIT")
      .map(([stage_instance_id, access]) => ({
        stage_instance_id,
        access: access as "VIEW" | "EDIT",
      }));

    await onSave(assignments);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Manage stage access</h2>
            <p className="mt-1 text-sm text-slate-500">
              {member.display_name} · {member.email}
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-xl text-slate-400 hover:text-slate-700">
            ×
          </button>
        </div>

        <div className="space-y-3 px-6 py-5">
          {stages.length === 0 ? (
            <p className="text-sm text-slate-500">No stages are configured for this project.</p>
          ) : (
            stages.map((stage) => {
              const disabled = !enabledStageIds.has(stage.stage_instance_id);
              return (
                <div key={stage.stage_instance_id} className="flex items-center justify-between rounded border border-slate-200 px-4 py-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{stageLabel(stage)}</div>
                    <div className="text-xs text-slate-400">
                      Stage ID: {stage.stage_instance_id}
                      {!enabledStageIds.has(stage.stage_instance_id) ? " · Disabled" : ""}
                    </div>
                  </div>
                  <select
                    value={form[stage.stage_instance_id] ?? ""}
                    disabled={disabled || saving}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        [stage.stage_instance_id]: e.target.value as "" | "VIEW" | "EDIT",
                      }))
                    }
                    className="rounded border border-slate-300 px-3 py-2 text-sm"
                  >
                    <option value="">No access</option>
                    {ACCESS_OPTIONS.map((access) => (
                      <option key={access} value={access}>
                        {access === "VIEW" ? "View" : "Edit"}
                      </option>
                    ))}
                  </select>
                </div>
              );
            })
          )}
        </div>

        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <button type="button" onClick={onClose} disabled={saving} className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700">
            Cancel
          </button>
          <button type="button" onClick={submit} disabled={saving} className="rounded bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            {saving ? "Saving…" : "Save access"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function StageAccessManager() {
  const { success, error } = useToast();
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [selectedProjectAccess, setSelectedProjectAccess] = useState<ProjectAccess | null>(null);
  const [projectDetails, setProjectDetails] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [accessLoading, setAccessLoading] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [editingMember, setEditingMember] = useState<ProjectAccessMember | null>(null);
  const [saving, setSaving] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const [projectList, orgUsers] = await Promise.all([
          ProjectsService.fetchAllProjects(),
          orgAdminService.fetchOrgUsers(true),
        ]);

        if (cancelled) return;

        const normalizedProjects = (Array.isArray(projectList) ? projectList : []).map((item: any) => ({
          id: String(item.id),
          project_name: item.project_name,
          projectName: item.projectName,
        }));

        const normalizedUsers = (Array.isArray(orgUsers) ? orgUsers : []).map((item: any) => ({
          id: String(item.id ?? item.user_id),
          name: item.display_name || item.name || item.email || "Unknown",
          email: item.email || "",
          has_org_admin_role: Boolean(item.has_org_admin_role),
        }));

        setProjects(normalizedProjects);
        setUsers(normalizedUsers);
        if (normalizedProjects[0]) setSelectedProjectId(normalizedProjects[0].id);
      } catch {
        if (!cancelled) error("Failed to load stage access administration data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [error]);

  useEffect(() => {
    if (!selectedProjectId) {
      setSelectedProjectAccess(null);
      setProjectDetails(null);
      return;
    }

    let cancelled = false;
    setAccessLoading(true);

    Promise.all([
      ProjectAccessService.fetchProjectAccess(selectedProjectId),
      ProjectsService.fetchProjectDetails(selectedProjectId),
    ])
      .then(([access, details]) => {
        if (cancelled) return;
        setSelectedProjectAccess(access);
        setProjectDetails(details as ProjectDetail);
      })
      .catch(() => {
        if (!cancelled) {
          setSelectedProjectAccess(null);
          setProjectDetails(null);
          error("Failed to load stage access for this project.");
        }
      })
      .finally(() => {
        if (!cancelled) setAccessLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedProjectId, error]);

  const enabledStageIds = useMemo(() => {
    const configs = projectDetails?.stage_configs ?? [];
    const recurring = projectDetails?.project_class === "RECURRING";
    const enabled = new Set<string>();

    for (const stage of selectedProjectAccess?.stages ?? []) {
      if (stage.stage === "RECURRING") {
        if (recurring) enabled.add(stage.stage_instance_id);
        continue;
      }

      const config = configs.find((item) => item.stage === stage.stage);
      if (config?.enabled === true) enabled.add(stage.stage_instance_id);
    }

    return enabled;
  }, [projectDetails, selectedProjectAccess]);

  const stages = useMemo(
    () => selectedProjectAccess?.stages ?? [],
    [selectedProjectAccess],
  );

  const members = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const source = selectedProjectAccess?.members ?? [];
    if (!needle) return source;
    return source.filter(
      (member) =>
        member.display_name.toLowerCase().includes(needle) ||
        member.email.toLowerCase().includes(needle),
    );
  }, [query, selectedProjectAccess]);

  const projectAdminIds = useMemo(() => {
    const ids = new Set<string>();
    for (const member of selectedProjectAccess?.members ?? []) {
      if (member.assignments.some((assignment) => assignment.access === "ADMIN")) {
        ids.add(member.user_id);
      }
    }
    return ids;
  }, [selectedProjectAccess]);

  const selectableUsers = useMemo(
    () =>
      users.filter(
        (user) =>
          !user.has_org_admin_role &&
          !projectAdminIds.has(user.id),
      ),
    [projectAdminIds, users],
  );

  const selectedUser = selectableUsers.find((user) => user.id === selectedUserId);

  const openNewMember = () => {
    setEditingMember({
      user_id: selectedUser?.id ?? selectedUserId,
      display_name: selectedUser?.name ?? "",
      email: selectedUser?.email ?? "",
      assignments: [],
    });
  };

  const saveMember = async (assignments: ProjectStageAssignment[]) => {
    if (!selectedProjectId || !editingMember?.user_id) return;
    setSaving(true);
    try {
      const updated = await ProjectAccessService.updateUserStageAccess(
        selectedProjectId,
        editingMember.user_id,
        assignments.filter((assignment) => enabledStageIds.has(assignment.stage_instance_id)),
      );
      setSelectedProjectAccess(updated);
      setEditingMember(null);
      setSelectedUserId("");
      success("Stage access updated.");
    } catch (err: any) {
      error(err?.response?.data?.detail || err?.message || "Failed to update stage access.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-sm text-slate-500">Loading stage access…</div>;
  }

  const selectedProject = projects.find((project) => project.id === selectedProjectId);

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-light text-text-dark">Stage access</h2>
        <p className="mt-1 text-sm text-slate-500">
          Assign View or Edit access independently for each project stage.
        </p>
      </div>

      <div className="rounded border border-slate-200 bg-white p-5">
        <label className="mb-2 block text-sm font-medium text-slate-700">Project</label>
        <select
          value={selectedProjectId}
          onChange={(event) => {
            setSelectedProjectId(event.target.value);
            setSelectedUserId("");
            setQuery("");
          }}
          className="w-full max-w-xl rounded border border-slate-300 px-3 py-2 text-sm"
        >
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.project_name || project.projectName || project.id}
            </option>
          ))}
        </select>
      </div>

      {accessLoading ? (
        <div className="text-sm text-slate-500">Loading stage access…</div>
      ) : selectedProjectAccess ? (
        <>
          <div className="rounded border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-5 py-4">
              <div className="text-base font-medium text-slate-900">{selectedProject?.project_name || selectedProject?.projectName}</div>
              <div className="mt-1 text-sm text-slate-500">
                {enabledStageIds.size} enabled stage{enabledStageIds.size === 1 ? "" : "s"}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 border-b bg-slate-50 p-4 md:grid-cols-[1fr_auto]">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search members…"
                className="rounded border border-slate-300 bg-white px-3 py-2 text-sm"
              />
              <div className="flex gap-2">
                <select
                  value={selectedUserId}
                  onChange={(event) => setSelectedUserId(event.target.value)}
                  className="rounded border border-slate-300 bg-white px-3 py-2 text-sm"
                >
                  <option value="">Select a user to add</option>
                  {selectableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name} — {user.email}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={!selectedUserId}
                  onClick={openNewMember}
                  className="rounded bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
                >
                  Add access
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-[#F7F7F7] text-xs uppercase tracking-wide text-slate-600">
                  <tr>
                    <th className="px-5 py-3 text-left">Member</th>
                    {stages.map((stage) => (
                      <th key={stage.stage_instance_id} className="px-5 py-3 text-left">
                        {stageLabel(stage)}
                      </th>
                    ))}
                    <th className="px-5 py-3 text-left">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => {
                    const projectAdmin = member.assignments.some((assignment) => assignment.access === "ADMIN");
                    return (
                      <tr key={member.user_id} className="border-t border-slate-100">
                        <td className="px-5 py-4">
                          <div className="font-medium text-slate-800">{member.display_name}</div>
                          <div className="text-xs text-slate-500">{member.email}</div>
                        </td>
                        {stages.map((stage) => {
                          const assignment = member.assignments.find(
                            (item) => item.stage_instance_id === stage.stage_instance_id,
                          );
                          return (
                            <td key={stage.stage_instance_id} className="px-5 py-4">
                              {!enabledStageIds.has(stage.stage_instance_id) ? (
                                <span className="text-slate-400">Disabled</span>
                              ) : assignment?.access === "ADMIN" && projectAdmin ? (
                                <span className="font-medium text-slate-800">Admin</span>
                              ) : (
                                accessLabel(assignment?.access ?? "NONE")
                              )}
                            </td>
                          );
                        })}
                        <td className="px-5 py-4">
                          {projectAdmin ? (
                            <span className="text-xs text-slate-400">Project admin</span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setEditingMember(member)}
                              className="text-sm font-medium text-primary"
                            >
                              Manage
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}

                  {members.length === 0 && (
                    <tr>
                      <td colSpan={stages.length + 2} className="px-5 py-8 text-center text-sm text-slate-500">
                        No users currently have stage access to this project.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <StageAccessEditModal
            open={Boolean(editingMember)}
            member={editingMember}
            stages={stages}
            onClose={() => setEditingMember(null)}
            onSave={saveMember}
            saving={saving}
            enabledStageIds={enabledStageIds}
          />
        </>
      ) : (
        <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Select a project to manage its stage access.
        </div>
      )}
    </section>
  );
}
