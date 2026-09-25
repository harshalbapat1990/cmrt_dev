import React, { useEffect, useMemo, useState } from "react";
import AccessTable from "../../components/AccessTable";
import ReviewModal from "../../components/ReviewModal";
import type { AdminAccessRequest } from "../../types/access";
import { useToast } from "../../components/common/ToastProvider";
import useDebounce from "../../customHooks/useDebounce";
import alertIconUrl from '../../assets/icons/emergency_home.svg'; 
import editIconUrl from '../../assets/icons/edit.svg';
import SearchInput from "../../components/SearchInput";
import accessRequestsService from "../../services/accessRequests.service";
import userRolesService, { type UserRoleEnriched } from "../../services/userRoles.service";
import http from "@/http";

type SortDir = "asc" | "desc";
type SortBy = "requester" | "projectName" | "dateRequested";
type TabKey = "review" | "projects";

const AdminAccessPage: React.FC = () => {
  const { success, error } = useToast();
  const [tab, setTab] = useState<TabKey>("review");

  const [items, setItems] = useState<AdminAccessRequest[]>([]);
  const [, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    accessRequestsService
      .fetchPending()
      .then((raw) => {
        if (cancelled) return;
        const projectLevel = raw.filter((r) =>
          ['PROJECT_EDITOR', 'PROJECT_VIEWER'].includes(r.request_type)
        );
        setItems(
          projectLevel.map((r) => ({
            id: r.id,
            requester: r.requester_display_name || r.requester_email || 'Unknown',
            projectName: r.project_name || '',
            projectCategory: '',
            stages: [],
            dateRequested: r.created_on || '',
            justification: r.reason || undefined,
            requestedRole: r.request_type,
          }))
        );
      })
      .catch(() => {
        if (!cancelled) error('Failed to load access requests.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const [sortBy] = useState<SortBy>("dateRequested");
  const [sortDir] = useState<SortDir>("asc");

  const filtered = useMemo(() => {
    return items;
  }, [items]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      if (sortBy === "dateRequested") {
        const cmp = a.dateRequested.localeCompare(b.dateRequested);
        return sortDir === "asc" ? cmp : -cmp;
      }
      const valA = (sortBy === "requester" ? a.requester : a.projectName) ?? "";
      const valB = (sortBy === "requester" ? b.requester : b.projectName) ?? "";
      const cmp = valA.localeCompare(valB);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [filtered, sortBy, sortDir]);

  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<AdminAccessRequest | null>(null);

  const openModal = (r: AdminAccessRequest) => {
    setSelected(r);
    setOpen(true);
  };
  const closeModal = () => {
    setOpen(false);
    setTimeout(() => setSelected(null), 200);
  };

  const handleApprove = async (r: AdminAccessRequest) => {
    try {
      await accessRequestsService.approve(r.id);
      setItems((prev) => prev.filter((x) => x.id !== r.id));
      success(`Access request for ${r.requester} has been approved`);
    } catch (e: any) {
      if (e?.response?.status === 409) {
        setItems((prev) => prev.filter((x) => x.id !== r.id));
        error('This request was already reviewed by another admin.');
      } else {
        error('Failed to approve. Please try again.');
      }
    } finally {
      closeModal();
    }
  };

  const handleReject = async (r: AdminAccessRequest, reason: string) => {
    try {
      await accessRequestsService.reject(r.id, reason);
      setItems((prev) => prev.filter((x) => x.id !== r.id));
      success(`Access request for ${r.requester} has been rejected`);
    } catch (e: any) {
      if (e?.response?.status === 409) {
        setItems((prev) => prev.filter((x) => x.id !== r.id));
        error('This request was already reviewed by another admin.');
      } else {
        error('Failed to reject. Please try again.');
      }
    } finally {
      closeModal();
    }
  };

  return (
    <div className="min-h-screen text-slate-800">
      <div className="mx-auto mt-12 max-w-7xl">
        <h2 className="mb-8 text-3xl font-light text-text-dark">Manage user access</h2>

        <div className="mb-6 border-b-2 border-[#ADADAD]">
          <div className="flex gap-6">
            <TabButton active={tab === "review"} onClick={() => setTab("review")}>
              Review access requests
            </TabButton>
          </div>
        </div>

        <AccessTable
          items={sorted}
          onOpen={openModal}
          maxHeight={560}
          sortByProp={sortBy === "dateRequested" ? sortBy : undefined}
          sortDirProp={sortDir}
        />
      </div>

      <ReviewModal
        open={open}
        request={selected}
        formerror="Reason for rejection is required"
        onClose={closeModal}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </div>
  );
};

export default AdminAccessPage;

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
      className={`relative -mb-px px-2 sm:px-3 cursor-pointer py-3 text-sm transition-colors ${
        active ? "font-medium text-primary" : "text-text-base hover:text-slate-800"
      }`}
      aria-current={active ? "page" : undefined}
    >
      {children}
      {active && <span className="absolute inset-x-0 -bottom-px block h-0.5 bg-primary" />}
    </button>
  );
}


type AccessLevel = "View" | "Edit" | "No access";
type StageName = "Business case" | "Design" | "Construction"|"N/A";

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
  const access: AccessLevel = roleName === 'PROJECT_EDITOR' ? 'Edit' : 'View';
  return [
    { stage: 'Business case', access },
    { stage: 'Design', access },
    { stage: 'Construction', access },
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
      http.get('/api/me/projects'),
      userRolesService.fetchEnriched({ scope_type: 'PROJECT', limit: 1000 }),
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
        const categoryMap: Record<string, string> = { SMALL: 'Small', LARGE: 'Large', RECURRING: 'Recurring' };
        const rows: ProjectRow[] = apiProjects.map((p: any) => {
          const members = (rolesByProject[p.id] ?? [])
            .filter((ur) => ['PROJECT_EDITOR', 'PROJECT_VIEWER'].includes(ur.role_name))
            .map((ur) => ({
              id: ur.user_id,
              name: ur.user_display_name || ur.user_email,
              email: ur.user_email,
              assignments: roleToAssignments(ur.role_name),
            }));
          return {
            id: p.id,
            name: p.project_name,
            program: p.program_name ?? '',
            category: categoryMap[p.project_class ?? ''] ?? p.project_class ?? '-',
            users: members.length,
            dateCreated: p.created_on ? String(p.created_on).slice(0, 10) : '',
            members,
          };
        });
        setProjects(rows);
      })
      .catch(() => { if (!cancelled) setProjects([]); })
      .finally(() => { if (!cancelled) setPanelLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const items = useMemo(() => {
    const needle = debouncedQ.trim().toLowerCase();
    const filtered = !needle ? projects : projects.filter((p) =>
      `${p.name} ${p.program}`.toLowerCase().includes(needle)
    );

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
          users: newMembers.length
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
    <section className="overflow-hidden rounded-[var(--radius-3)] border border-slate-200 bg-white">
      <div className="px-6 py-5">
        <h3 className="text-2xl font-light text-text-dark">Projects ({panelLoading ? '…' : items.length})</h3>
      </div>

    <div className="px-6 pt-4 mb-6">
      <SearchInput
        value={q}
        onChange={setQ}
        placeholder="Search by project or program name"
        className="w-98"
      />
    </div>

      <div className="max-h-[220px] overflow-y-auto scroll-styled no-scroll-buttons" style={{ maxHeight: 560, minHeight: 220 }}>
        {panelLoading ? (
          <div className="flex items-center justify-center h-[220px]">
            <span className="text-text-faint text-sm">Loading projects...</span>
          </div>
        ) : items.length === 0 && !debouncedQ ? (
          <div className="flex items-center justify-center h-[220px]">
            <span className="text-text-faint text-sm">No projects yet</span>
          </div>
        ) : items.length === 0 && debouncedQ ? (
          <div className="flex items-center justify-center h-[220px]">
            <span className="text-text-faint text-sm">No projects match your search</span>
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="text-text-base  ">
              <tr className="border-b h-full  border-slate-200 px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-text-base bg-[#F7F7F7]">
                <th className="text-left font-medium pb-3 pt-3 pl-6">PROJECT NAME</th>
                <th className="text-left font-medium pb-3 pt-3 pl-6">PROJECT CATEGORY</th>
                <th className="text-left font-medium pb-3 pt-3 pl-6">NUMBER OF USERS</th>
                <th className="text-left font-medium pb-3 pt-3 pl-6">
                  <div className="flex items-center gap-1">
                    <span>DATE CREATED</span>
                    <button
                      type="button"
                      onClick={toggleDateSort}
                      className="inline-flex items-center cursor-pointer rounded p-1  "
                      aria-label="Sort by date created"
                      title="Sort by date created"
                    >
                      <span
                        className="material-symbols-rounded text-gray-500"
                        style={{ fontSize: 18 }}
                      >
                        {sortBy === "dateCreated" && (
                          sortDir === "asc" ? "arrow_drop_up" : "arrow_drop_down"
                        )}
                      </span>
                    </button>
                  </div>
                </th>
                <th className="text-left font-medium pb-3">ACTION</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => {
                
                const isEven = items.findIndex((r: ProjectRow) => r.id === p.id) % 2 === 0;
                return(
                  <>
                  <tr key={p.id} className={`border-b border-slate-100 ml-6 h-15 ${isEven ? "bg-white" : "bg-[#FAFAFA]"}`}>
                    <td className="px-4 py-3 text-sm text-slate-800 align-middle border-t  border-slate-100">
                      <div className="text-text-table-cell text-sm">{p.name}</div>
                      {p.program && <div className="text-xs text-slate-500">{p.program}</div>}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-800 align-middle border-t  border-slate-100 ">
                      {p.category}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-800 align-middle border-t  border-slate-100 ">
                      {p.users}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-800 align-middle border-t  border-slate-100 ">
                      {formatDate(p.dateCreated)}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-800 align-middle border-t  border-slate-100 ">
                      <button
                        onClick={() => openAccessModal(p)}
                        className="text-sm cursor-pointer text-primary font-medium"
                      >
                        Manage access
                      </button>
                    </td>
                  </tr>
                  </>
                )
               
              })}
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
  onRemoveMember
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
      rowSpan: member.assignments.length
    }));

    if (rows.length === 0) {
      return [{
        key: `${member.id}--empty`,
        member,
        assignment: { stage: "N/A", access: "View" } as unknown as MemberAssignment,
        isFirst: true,
        isLast: true,
        rowSpan: 1
      }];
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
          <div className="max-h-[360px] " >
            <div className="max-h-[220px] overflow-y-auto scroll-styled no-scroll-buttons">
              <table className="w-full border-collapse" style={{ borderSpacing: 0 }}>
                <thead className="sticky top-0 z-10 bg-neutral-90">
                  <tr className="border-b-1 border-neutral-90">
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-base border-r-2 border-neutral-90"  style={{ position: "sticky", top: 0 }}>
                      Name
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-base border-r-2 border-neutral-90"  style={{ position: "sticky", top: 0 }}>
                      Project stage
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-base border-r-2 border-neutral-90"  style={{ position: "sticky", top: 0 }}>
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
                      className="px-6 py-6 text-sm text-text-base border-b-1 border-neutral-90"
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
                              className="px-5 py-4 align-top text-left border-r-1 border-neutral-90"
                              rowSpan={rowSpan}
                              style={{
                                borderTop: '1px solid rgb(232, 232, 232)',
                                borderBottom: '1px solid rgb(232, 232, 232)',
                              }}
                            >
                              <div className="flex flex-col gap-1">
                                <div className="text-[15px] text-text-dark">{member.name}</div>
                                <div className="text-xs text-text-faint">{member.email}</div>
                              </div>
                            </td>
                          )}

                          <td className="px-5 py-4 text-text-table-cell border-r-1 border-b-1 border-neutral-90">
                            {assignment.stage}
                          </td>

                          <td className="px-5 py-4 text-text-table-cell border-r-1 border-b-1 border-neutral-90">
                            {assignment.access}
                          </td>

{isFirst && (
  <td
    rowSpan={rowSpan}
    className="px-5 py-0 border-b-1 border-neutral-90"
    style={{
      borderTop: '1px solid rgb(232, 232, 232)',
      borderBottom: '1px solid rgb(232, 232, 232)',
      verticalAlign: 'middle'
    }}
  >
    <div className="h-full min-h-full flex items-center justify-center gap-5 py-4">
      <button
        className="inline-flex items-center cursor-pointer gap-1 text-sm text-primary"
        onClick={() => onEditMember(member)}
      >
        <img
          src={editIconUrl}
          alt="Edit"
          className="w-4 h-4"
          aria-hidden
        />
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
              className=" px-4 py-2 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium text-text-table-cell bg-white border border-text-table-cell hover:bg-neutral-95"
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
  onSave
}: {
  open: boolean;
  member: ProjectMember | null;
  project: ProjectRow | null;
  onClose: () => void;
  onSave: (memberId: string, nextAssignments: MemberAssignment[]) => void;
}) {
  if (!open || !member || !project) return null;

  const ORDER: StageName[] = ["Business case", "Design", "Construction",];
  const foundStages = Array.from(
    new Set(project.members.flatMap((m) => m.assignments.map((a) => a.stage)))
  ) as StageName[];
  const stages = [
    ...ORDER.filter((s) => foundStages.includes(s)),
    ...foundStages.filter((s) => !ORDER.includes(s))
  ];

  const [form, setForm] = useState<Record<string, AccessLevel | "" >>({});
  const [initial, setInitial] = useState<Record<string, AccessLevel | "" >>({});
  const [showDiscard, setShowDiscard] = useState(false);

  useEffect(() => {
    const init: Record<string, AccessLevel | "" > = {};
    stages.forEach((s) => {
      const match = member.assignments.find((a) => a.stage === s);
      init[s] = match ? match.access : "";
    });
    setInitial(init);
    setForm(init);
    setShowDiscard(false);
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
            <div className=" font-medium mb-1 text-text-dark text-base">
              Project stage access
            </div>
            <div className="text-text-faint text-sm mb-4">
              Select the access type required for each project stage
            </div>

            <div className="overflow-hidden ">
              <table className="w-full text-sm">
                <thead className="border-b border-light-grey">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-xs text-text-dark">PROJECT STAGES</th>
                    <th className="px-4 py-2 text-left font-medium text-xs text-text-dark">VIEW</th>
                    <th className="px-4 py-2 text-left font-medium text-xs text-text-dark">EDIT</th>
                     <th className="px-4 py-2 text-left font-medium text-xs text-text-dark">NO ACCESS</th>
                  </tr>
                </thead>

                <tbody>
                  {stages.map((stage) => (
                    <tr key={stage} className="border-b border-light-grey">
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
                className="text-text-table-cell cursor-pointer font-medium bg-white px-4 py-2 text-sm"
              >
                Cancel
              </button>

              <button
                onClick={handleSave}
                className="rounded-[var(--radius-3)] px-4.5 py-2.5 cursor-pointer text-sm font-medium text-white bg-primary">
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
            <p className="text-slate-700 mb-6">
              You have unsaved changes to{" "}
              <span className="font-medium">{member.name}’s</span> access.
              Closing will discard these changes.
            </p>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDiscard(false)}
                className="rounded border border-slate-300 cursor-pointer bg-white px-4 py-2 text-sm"
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
  onConfirm
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
           <img src={alertIconUrl} alt="" width={25} height={25} aria-hidden="true" className = "mt-1"/>
          <h3 id="remove-user-title" className="text-2xl font-light text-slate-900">
            Remove user from project
          </h3>
        </div>

        <p className="text-slate-700 mb-12">
          You’re about to remove <span className="font-medium">{member.name}</span> from{" "}
          <span className="font-medium">{project.name}</span>. All access permissions will be revoked.
        </p>

        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="text-text-table-cell cursor-pointer px-4 py-2 text-sm font-medium"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded bg-red-700 px-4 py-2 cursor-pointer text-sm font-medium text-white hover:bg-red-800"
          >
            Remove user
          </button>
        </div>
      </div>
    </div>
  );
}

function formatDate(input: string) {
  const isoMatch = /^\d{4}-\d{2}-\d{2}$/.test(input);
  if (!isoMatch) return input;
  const d = new Date(input + "T00:00:00");
  const day = d.getDate();
  const month = d.toLocaleString("en-GB", { month: "long" });
  const year = d.getFullYear();
  return `${day} ${month} ${year}`;
}
