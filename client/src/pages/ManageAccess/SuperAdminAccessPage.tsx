import React, { useEffect, useMemo, useState } from "react";
import type { SuperAdminAccessRequest } from "../../types/access";
import { useToast } from "../../components/common/ToastProvider";
import alertIconUrl from "../../assets/icons/emergency_home.svg";
import accessRequestsService from "../../services/accessRequests.service";
import userRolesService, { type UserRoleEnriched } from "../../services/userRoles.service";
import orgAdminService, { type OrgUser } from "../../services/orgAdmin.service";

const th =
  "px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-text-base bg-[#F7F7F7]";
const td =
  "px-4 py-3 text-sm text-slate-800  border-t  border-slate-100 align-middle";

const SuperAdminAccessPage: React.FC = () => {
  const { success, error } = useToast();

  const [items, setItems] = useState<SuperAdminAccessRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      accessRequestsService.fetchPending('ORG_ADMIN'),
      accessRequestsService.fetchPending('SUPER_ADMIN'),
    ])
      .then(([orgAdmin, superAdmin]) => {
        if (cancelled) return;
        const combined = [...orgAdmin, ...superAdmin];
        setItems(
          combined.map((r) => ({
            id: r.id,
            requestedBy: r.requester_display_name || r.requester_email || 'Unknown',
            email: r.requester_email || '',
            organisation: r.organisation_name || 'Unknown',
            dateRequested: r.created_on || '',
            action: 'Review request',
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

  const [orgAdmins, setOrgAdmins] = useState<UserRoleEnriched[]>([]);
  const [orgAdminsLoading, setOrgAdminsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    userRolesService
      .fetchEnriched({ scope_type: 'ORGANISATION', role_name: 'ORG_ADMIN', limit: 500 })
      .then((data) => { if (!cancelled) setOrgAdmins(data); })
      .catch(() => { if (!cancelled) error('Failed to load organisation admins.'); })
      .finally(() => { if (!cancelled) setOrgAdminsLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const orgAdminsByOrg = useMemo(() => {
    const groups: Record<string, UserRoleEnriched[]> = {};
    for (const ur of orgAdmins) {
      const key = ur.org_name || 'Unknown Organisation';
      if (!groups[key]) groups[key] = [];
      groups[key].push(ur);
    }
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  }, [orgAdmins]);

  const [removeTarget, setRemoveTarget] = useState<UserRoleEnriched | null>(null);
  const [transferTarget, setTransferTarget] = useState<UserRoleEnriched | null>(null);
  const [addTarget, setAddTarget] = useState<{ orgId: string; orgName: string } | null>(null);

  const handleRemoveOrgAdmin = async (m: UserRoleEnriched) => {
    try {
      await userRolesService.revokeRole(m.user_role_id);
      setOrgAdmins((prev) => prev.filter((x) => x.user_role_id !== m.user_role_id));
      success(`${m.user_display_name || m.user_email} removed as Org Admin`);
    } catch {
      error('Failed to remove. Please try again.');
    } finally {
      setRemoveTarget(null);
    }
  };

  const handleTransferOrgAdmin = async (fromMember: UserRoleEnriched, toUserId: string) => {
    try {
      await userRolesService.transferOrgAdmin(fromMember.user_role_id, toUserId);
      const updated = await userRolesService.fetchEnriched({ scope_type: 'ORGANISATION', role_name: 'ORG_ADMIN', limit: 500 });
      setOrgAdmins(updated);
      success('ORG_ADMIN role transferred successfully');
    } catch {
      error('Failed to transfer. Please try again.');
    } finally {
      setTransferTarget(null);
    }
  };

  const handleAddOrgAdmin = async (orgId: string, userId: string) => {
    try {
      await userRolesService.assignOrgAdminForSA(orgId, userId);
      const updated = await userRolesService.fetchEnriched({ scope_type: 'ORGANISATION', role_name: 'ORG_ADMIN', limit: 500 });
      setOrgAdmins(updated);
      success('User assigned as Org Admin successfully');
    } catch {
      error('Failed to assign. Please try again.');
    } finally {
      setAddTarget(null);
    }
  };

  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<SuperAdminAccessRequest | null>(null);

  const openModal = (r: SuperAdminAccessRequest) => {
    setSelected(r);
    setOpen(true);
  };
  const closeModal = () => {
    setOpen(false);
    setTimeout(() => setSelected(null), 200);
  };

  type SortDir = "asc" | "desc";
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  function parseISO(dateStr: string): number {
    const iso = /^\d{4}-\d{2}-\d{2}$/.test(dateStr)
      ? new Date(dateStr + "T00:00:00")
      : new Date(dateStr);
    return iso.getTime();
  }

  const sorted = useMemo(() => {
    const copy = [...items];
    copy.sort((a, b) => {
      const at = parseISO(a.dateRequested);
      const bt = parseISO(b.dateRequested);
      const cmp = at === bt ? 0 : at < bt ? -1 : 1;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [items, sortDir]);

  const toggleDateSort = () => {
    setSortDir((d) => (d === "asc" ? "desc" : "asc"));
  };

  const handleApprove = async (r: SuperAdminAccessRequest) => {
    try {
      await accessRequestsService.approve(r.id);
      setItems((prev) => prev.filter((x) => x.id !== r.id));
      success(`Access request for ${r.requestedBy} has been approved`);
    } catch {
      error("Failed to approve. Please try again.");
    } finally {
      closeModal();
    }
  };

  const handleReject = async (r: SuperAdminAccessRequest, reason: string) => {
    try {
      await accessRequestsService.reject(r.id, reason);
      setItems((prev) => prev.filter((x) => x.id !== r.id));
      success(`Access request for ${r.requestedBy} has been rejected`);
    } catch {
      error("Failed to reject. Please try again.");
    } finally {
      closeModal();
    }
  };

  return (
    <div className="min-h-screen text-slate-800">
      <div className="mx-auto mt-12 max-w-7xl">
        <h2 className="mb-6 text-3xl font-light text-slate-700">
          Review requests for administrator access
        </h2>

        <section className="overflow-hidden rounded-[var(--radius-3)] border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-6 py-5">
            <h3 className="text-2xl font-light text-slate-900">Pending ({loading ? '…' : sorted.length})</h3>
          </div>

          <div className="overflow-y-auto" style={{ maxHeight: 560 }}>
            <table className="min-w-full border-separate" style={{ borderSpacing: 0 }}>
              <thead className="bg-[#F7F7F7]">
                <tr>
                  <th className={th} style={{ position: "sticky", top: 0 }}>
                    Requested by
                  </th>
                  <th className={th} style={{ position: "sticky", top: 0 }}>
                    Email
                  </th>
                  <th className={th} style={{ position: "sticky", top: 0 }}>
                    Organisation
                  </th>
                  <th className={th} style={{ position: "sticky", top: 0 }}>
                    <div className="flex items-center gap-1">
                      <span>Date requested</span>
                      <button
                        type="button"
                        onClick={toggleDateSort}
                        className="inline-flex items-center rounded cursor-pointer p-1 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-300"
                        aria-label="Sort by date requested"
                        title="Sort by date requested"
                      >
                        <span className="material-symbols-rounded text-gray-500" style={{ fontSize: 18 }}>
                          {sortDir === "asc" ? "arrow_drop_up" : "arrow_drop_down"}
                        </span>
                      </button>
                    </div>
                  </th>
                  <th className={th} style={{ position: "sticky", top: 0 }}>
                    Action
                  </th>
                </tr>
              </thead>

              <tbody>
                {sorted.length === 0 ? (
                  <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-sm text-slate-500">
                    No pending requests.
                  </td>
                  </tr>
                ) : (
                  sorted.map((r, index) => {
                  const isEven = index % 2 === 0;
                  return (
                    <tr key={r.id} className={`border-b border-slate-100 ml-6 h-15 ${isEven ? "bg-white" : "bg-[#FAFAFA]"}`}>
                    <td className={td}>{r.requestedBy}</td>
                    <td className={td}>{r.email}</td>
                    <td className={td}>{r.organisation}</td>
                    <td className={td}>{formatDate(r.dateRequested)}</td>
                    <td className={td}>
                      <button
                      className="text-primary cursor-pointer hover:opacity-90 text-sm font-medium"
                      onClick={() => openModal(r)}
                      >
                      Review request
                      </button>
                    </td>
                    </tr>
                  );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-8 overflow-hidden rounded-[var(--radius-3)] border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-6 py-5">
            <h3 className="text-2xl font-light text-slate-900">
              Organisation Admins {!orgAdminsLoading && `(${orgAdmins.length})`}
            </h3>
          </div>

          {orgAdminsLoading ? (
            <div className="px-6 py-8 text-sm text-slate-500">Loading…</div>
          ) : orgAdminsByOrg.length === 0 ? (
            <div className="px-6 py-8 text-sm text-slate-500">No organisation admins found.</div>
          ) : (
            <OrgAdminGroupList
              groups={orgAdminsByOrg}
              onRemove={setRemoveTarget}
              onTransfer={setTransferTarget}
              onAdd={(orgId, orgName) => setAddTarget({ orgId, orgName })}
            />
          )}
        </section>
      </div>

      <SuperAdminReviewModal
        open={open}
        request={selected}
        formerror="Reason for rejection is required"
        onClose={closeModal}
        onApprove={handleApprove}
        onReject={handleReject}
      />

      <AddOrgAdminModal
        target={addTarget}
        onCancel={() => setAddTarget(null)}
        onConfirm={handleAddOrgAdmin}
      />

      <RemoveOrgAdminModal
        member={removeTarget}
        onCancel={() => setRemoveTarget(null)}
        onConfirm={handleRemoveOrgAdmin}
      />

      <TransferOrgAdminModal
        member={transferTarget}
        onCancel={() => setTransferTarget(null)}
        onConfirm={handleTransferOrgAdmin}
      />
    </div>
  );
};

export default SuperAdminAccessPage;

function OrgAdminGroupList({
  groups,
  onRemove,
  onTransfer,
  onAdd,
}: {
  groups: [string, UserRoleEnriched[]][];
  onRemove: (m: UserRoleEnriched) => void;
  onTransfer: (m: UserRoleEnriched) => void;
  onAdd: (orgId: string, orgName: string) => void;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const toggle = (key: string) =>
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <ul className="divide-y divide-slate-100">
      {groups.map(([orgName, members]) => {
        const isOpen = expanded[orgName] ?? false;
        const orgId = members[0]?.scope_id ?? '';
        return (
          <li key={orgName}>
            {/* Header uses a flex div so the add button can sit beside the toggle without nesting buttons */}
            <div className="flex w-full items-center hover:bg-slate-50">
              <button
                type="button"
                onClick={() => toggle(orgName)}
                className="flex flex-1 items-center cursor-pointer justify-between px-6 py-4 text-left focus:outline-none focus:ring-2 focus:ring-inset focus:ring-orange-300"
                aria-expanded={isOpen}
              >
                <span className="font-medium text-slate-800">{orgName}</span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{members.length} admin{members.length !== 1 ? 's' : ''}</span>
                  <span className="material-symbols-rounded text-slate-400" style={{ fontSize: 20 }}>
                    {isOpen ? 'expand_less' : 'expand_more'}
                  </span>
                </div>
              </button>
              <button
                type="button"
                onClick={() => onAdd(orgId, orgName)}
                title="Add Org Admin"
                className="mr-4 p-1 pt-2 rounded text-slate-400 hover:text-primary hover:bg-slate-100"
              >
                <span className="material-symbols-rounded" style={{ fontSize: 20 }}>person_add</span>
              </button>
            </div>
            {isOpen && (
              <ul className="border-t border-slate-50 bg-slate-50">
                {members.map((m) => (
                  <li
                    key={m.user_role_id}
                    className="flex items-center justify-between px-8 py-3 border-b border-slate-100 last:border-b-0"
                  >
                    <div>
                      <div className="text-sm font-medium text-slate-800">
                        {m.user_display_name || m.user_email}
                      </div>
                      {m.user_display_name && (
                        <div className="text-xs text-slate-500">{m.user_email}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-medium text-text-faint bg-slate-200 px-2 py-0.5 rounded">
                        Org Admin
                      </span>
                      <button
                        type="button"
                        onClick={() => onTransfer(m)}
                        title="Transfer Org Admin role"
                        className="p-1 rounded text-slate-500 hover:text-primary hover:bg-slate-100"
                      >
                        <span className="material-symbols-rounded" style={{ fontSize: 18 }}>swap_horiz</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => onRemove(m)}
                        title="Remove Org Admin"
                        className="p-1 rounded text-slate-500 hover:text-danger hover:bg-slate-100"
                      >
                        <span className="material-symbols-rounded" style={{ fontSize: 18 }}>person_remove</span>
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function SuperAdminReviewModal({
  open,
  request,
  formerror,
  onClose,
  onApprove,
  onReject
}: {
  open: boolean;
  request: SuperAdminAccessRequest | null;
  formerror: string;
  onClose: () => void;
  onApprove: (r: SuperAdminAccessRequest) => void;
  onReject: (r: SuperAdminAccessRequest, reason: string) => void;
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
      aria-labelledby="sa-review-title"
    >
      <div className="w-149 max-w-[95vw] rounded-md bg-white p-6 shadow-xl">
        <h3 id="sa-review-title" className="text-2xl font-light text-slate-900 mb-6">
          Review request for administrative access
        </h3>

        <div className="space-y-3 mb-4 text-sm">
          <div>
            <label className="mb-1 block text-xs font-medium text-text-faint">REQUESTED BY</label>
            <div className="text-slate-900 mb-3">{request.requestedBy}</div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-faint pt-2">EMAIL</label>
            <div className="text-slate-900 break-all mb-3">{request.email}</div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-faint pt-2">ORGANISATION</label>
            <div className="text-slate-900 mb-2">{request.organisation}</div>
          </div>
        </div>

        {mode === "rejecting" && (
          <div className="mb-6">
            <div className="mb-5">
              <div className="h-px bg-gray-100"></div>
            </div>
            <label htmlFor="reject-reason " className="mb-2 block text-xs font-medium text-text-faint">
              REASON FOR REJECTION (REQUIRED)
            </label>
            <textarea
              id="reject-reason"
              className={`w-full rounded-[var(--radius-3)] border px-3 py-2 text-sm outline-none ${
                showError
                  ? "border-2 border-danger text-danger"
                  : "border-slate-300 "
              }`}
              rows={4}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (showError) setShowError(false);
              }}
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

        <div className="mt-4 flex justify-start gap-72">
          <button onClick={onClose} className=" bg-white font-medium cursor-pointer px-4 py-2 text-sm text-text-table-cell ">
            Cancel
          </button>

          {mode === "idle" ? (
            <div className="flex gap-3">
              <button
                onClick={startReject}
                className="rounded border border-text-table-cell cursor-pointer font-medium bg-white px-4 py-2 text-sm text-text-table-cell"
              >
                Reject
              </button>
              <button
                onClick={approve}
                className=" rounded bg-primary px-4 py-2 cursor-pointer text-sm font-medium text-white"
              >
                Approve
              </button>
            </div>
          ) : (
            <button
              onClick={confirmReject}
              className="rounded-[var(--radius-3)] ml-11 cursor-pointer bg-primary px-4 py-2 text-sm font-medium text-white"
            >
              Confirm rejection
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function RemoveOrgAdminModal({
  member,
  onCancel,
  onConfirm,
}: {
  member: UserRoleEnriched | null;
  onCancel: () => void;
  onConfirm: (m: UserRoleEnriched) => Promise<void>;
}) {
  const [removing, setRemoving] = useState(false);
  if (!member) return null;

  const name = member.user_display_name || member.user_email;
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/30" role="dialog" aria-modal="true">
      <div className="w-96 max-w-[95vw] rounded-md bg-white p-6 shadow-xl">
        <h3 className="text-lg font-medium mb-4">Remove Org Admin</h3>
        <p className="text-sm text-slate-600 mb-6">
          Remove <span className="font-medium">{name}</span> as Org Admin for{' '}
          <span className="font-medium">{member.org_name}</span>?
          They will lose organisation-level admin access.
        </p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel} disabled={removing} className="text-sm px-4 py-2 text-slate-600">
            Cancel
          </button>
          <button
            disabled={removing}
            onClick={async () => {
              setRemoving(true);
              await onConfirm(member);
              setRemoving(false);
            }}
            className="rounded bg-danger px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {removing ? 'Removing…' : 'Remove'}
          </button>
        </div>
      </div>
    </div>
  );
}

function TransferOrgAdminModal({
  member,
  onCancel,
  onConfirm,
}: {
  member: UserRoleEnriched | null;
  onCancel: () => void;
  onConfirm: (from: UserRoleEnriched, toUserId: string) => Promise<void>;
}) {
  const [candidates, setCandidates] = useState<OrgUser[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [transferring, setTransferring] = useState(false);
  const { error } = useToast();

  useEffect(() => {
    if (!member?.scope_id) return;
    setLoadingCandidates(true);
    setSearch('');
    setSelectedId(null);
    orgAdminService
      .fetchOrgMembersForSA(member.scope_id)
      .then((users) => setCandidates(users.filter((u) => !u.has_org_admin_role)))
      .catch(() => error('Failed to load organisation members.'))
      .finally(() => setLoadingCandidates(false));
  }, [member?.user_role_id]);

  if (!member) return null;

  const fromName = member.user_display_name || member.user_email;
  const filtered = candidates.filter((u) => {
    const q = search.toLowerCase();
    return (u.display_name || u.name || '').toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
  });

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/30" role="dialog" aria-modal="true">
      <div className="w-[480px] max-w-[95vw] rounded-md bg-white p-6 shadow-xl">
        <h3 className="text-lg font-medium mb-2">Transfer Org Admin role</h3>
        <p className="text-sm text-slate-500 mb-4">
          Transfer <span className="font-medium text-slate-800">{fromName}</span>'s Org Admin role
          for <span className="font-medium text-slate-800">{member.org_name}</span> to another member.
        </p>

        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or email"
          className="w-full mb-3 px-3 py-2 text-sm border rounded-[var(--radius-3)] outline-none"
        />

        <div className="max-h-52 overflow-y-auto border rounded mb-4">
          {loadingCandidates ? (
            <div className="px-4 py-6 text-sm text-slate-500 text-center">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="px-4 py-6 text-sm text-slate-500 text-center">No eligible members found.</div>
          ) : (
            filtered.map((u) => {
              const label = u.display_name || u.name || u.email;
              return (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => setSelectedId(u.id)}
                  className={`w-full text-left px-4 py-3 border-b last:border-b-0 text-sm hover:bg-slate-50 ${
                    selectedId === u.id ? 'bg-orange-50 font-medium' : ''
                  }`}
                >
                  <div>{label}</div>
                  <div className="text-xs text-slate-500">{u.email}</div>
                </button>
              );
            })
          )}
        </div>

        <div className="flex justify-end gap-3">
          <button onClick={onCancel} disabled={transferring} className="text-sm px-4 py-2 text-slate-600">
            Cancel
          </button>
          <button
            disabled={!selectedId || transferring}
            onClick={async () => {
              if (!selectedId) return;
              setTransferring(true);
              await onConfirm(member, selectedId);
              setTransferring(false);
            }}
            className="rounded bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {transferring ? 'Transferring…' : 'Transfer'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AddOrgAdminModal({
  target,
  onCancel,
  onConfirm,
}: {
  target: { orgId: string; orgName: string } | null;
  onCancel: () => void;
  onConfirm: (orgId: string, userId: string) => Promise<void>;
}) {
  const [candidates, setCandidates] = useState<OrgUser[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const { error } = useToast();

  useEffect(() => {
    if (!target?.orgId) return;
    setLoadingCandidates(true);
    setSearch('');
    setSelectedId(null);
    orgAdminService
      .fetchOrgMembersForSA(target.orgId)
      .then((users) => setCandidates(users.filter((u) => !u.has_org_admin_role)))
      .catch(() => error('Failed to load organisation members.'))
      .finally(() => setLoadingCandidates(false));
  }, [target?.orgId]);

  if (!target) return null;

  const filtered = candidates.filter((u) => {
    const q = search.toLowerCase();
    return (u.display_name || u.name || '').toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
  });

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/30" role="dialog" aria-modal="true">
      <div className="w-[480px] max-w-[95vw] rounded-md bg-white p-6 shadow-xl">
        <h3 className="text-lg font-medium mb-2">Add Org Admin</h3>
        <p className="text-sm text-slate-500 mb-4">
          Select a member of <span className="font-medium text-slate-800">{target.orgName}</span> to assign as Org Admin.
        </p>

        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or email"
          className="w-full mb-3 px-3 py-2 text-sm border rounded-[var(--radius-3)] outline-none"
        />

        <div className="max-h-52 overflow-y-auto border rounded mb-4">
          {loadingCandidates ? (
            <div className="px-4 py-6 text-sm text-slate-500 text-center">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="px-4 py-6 text-sm text-slate-500 text-center">No eligible members found.</div>
          ) : (
            filtered.map((u) => {
              const label = u.display_name || u.name || u.email;
              return (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => setSelectedId(u.id)}
                  className={`w-full text-left px-4 py-3 border-b last:border-b-0 text-sm hover:bg-slate-50 ${
                    selectedId === u.id ? 'bg-orange-50 font-medium' : ''
                  }`}
                >
                  <div>{label}</div>
                  <div className="text-xs text-slate-500">{u.email}</div>
                </button>
              );
            })
          )}
        </div>

        <div className="flex justify-end gap-3">
          <button onClick={onCancel} disabled={adding} className="text-sm px-4 py-2 text-slate-600">
            Cancel
          </button>
          <button
            disabled={!selectedId || adding}
            onClick={async () => {
              if (!selectedId) return;
              setAdding(true);
              await onConfirm(target.orgId, selectedId);
              setAdding(false);
            }}
            className="rounded bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {adding ? 'Assigning…' : 'Assign as Org Admin'}
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
