import React, { useMemo, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import type { Project, StatusType, RoleType } from "../../../types/project";
import SearchInput from "../../../components/SearchInput";
import StatusFilter from "../../../components/StatusFilter";
import ProjectTable from "../../../components/ProjectTable";
import SummaryCard from "../../../components/SummaryCard";
import PaginationBar from "../../../components/PaginationBar";
import EmptyState from "../../../components/EmptySearch";
import useDebounce from "../../../customHooks/useDebounce";
import http from "@/http";
import { useUser } from "@/context/UserContext";
import ProjectAccess from "../../../components/ProjectAccess";
import { Modal } from "../../../components/common/Modal";

interface PendingActionItem {
  project_id: string;
  project_name: string;
  stage_instance_id: string;
  stage: "BUSINESS_CASE" | "DESIGN" | "CONSTRUCTION";
  report_number: number;
  num_reports_required: number;
  approval_status: "submitted" | "pending_reopen";
}

const STAGE_LABEL: Record<string, string> = {
  BUSINESS_CASE: "Business Case",
  DESIGN: "Design",
  CONSTRUCTION: "Construction",
};

// Types
type SortDir = "asc" | "desc";

interface Props {
  role: RoleType;
  data: Project[];
  showRequestAccessButton?: boolean;
  showProjectCreationButton?: boolean;
}

const ProjectsPage: React.FC<Props> = ({
  role,
  data,
  showRequestAccessButton,
  showProjectCreationButton,
}) => {
  const navigate = useNavigate();
  const {user} = useUser();

  // UI state
  const [search, setSearch] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState<StatusType[]>([]);
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(10);

  const [showRequestAccess, setShowRequestAccess] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const openRequestModal = () => setShowRequestAccess(true);
  const closeRequestModal = () => setShowRequestAccess(false);
  const openCancelModal = () => setShowCancelConfirm(true);
  const closeCancelModal = () => setShowCancelConfirm(false);

  // Pending report-level actions
  const [pendingActions, setPendingActions] = useState<PendingActionItem[]>([]);
  const [pendingExpanded, setPendingExpanded] = useState(false);
  const [reopenExpanded, setReopenExpanded] = useState(false);

  useEffect(() => {
    if (role === "user") return;
    http
      .get<PendingActionItem[]>("/api/me/pending-actions")
      .then((res) => setPendingActions(res.data))
      .catch(() => setPendingActions([]));
  }, [role]);

  const pendingApprovals = useMemo(
    () => pendingActions.filter((s) => s.approval_status === "submitted"),
    [pendingActions]
  );
  const pendingReopens = useMemo(
    () => pendingActions.filter((s) => s.approval_status === "pending_reopen"),
    [pendingActions]
  );

  const closeAllModals = () => {
    setShowRequestAccess(false);
    setShowCancelConfirm(false);
  };

  // Search debounce
  const debouncedSearch = useDebounce(search, 300);
  const effectiveQuery = debouncedSearch.trim().toLowerCase();
  const canSearch = effectiveQuery.length >= 1;

  // Toggle status from StatusFilter
  const toggleStatus = (status: StatusType) => {
    setSelectedStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status]
    );
  };
  const clearAll = () => setSelectedStatuses([]);

  // Reset to page 1 when inputs change (use debouncedSearch to avoid jumpiness)
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, selectedStatuses, sortDir, pageSize]);

  // 1) Apply status filter first (status filter is always active if selected)
  const statusFiltered = useMemo(() => {
    if (selectedStatuses.length === 0) return data;
    return data.filter((p: Project) => selectedStatuses.includes(p.status as StatusType));
  }, [data, selectedStatuses]);

  // 2) Apply text search 
  const filtered = useMemo(() => {
    if (!canSearch) return statusFiltered;

    return statusFiltered.filter((p: Project) => {
      const name = p.projectName?.toLowerCase() ?? "";
      const prog = p.programName?.toLowerCase() ?? "";
      return name.includes(effectiveQuery) || prog.includes(effectiveQuery);
    });
  }, [statusFiltered, effectiveQuery, canSearch]);

  // Helpers
  const isAwaitingApproval = (p: Project) =>
    (p.status ?? "").toString().trim().toLowerCase() === "awaiting approval";

  const getUpdatedAt = (p: Project) => {
    const t = p.lastUpdated ? new Date(p.lastUpdated).getTime() : NaN;
    // Missing/invalid dates count as oldest
    return Number.isNaN(t) ? -Infinity : t;
  };

  // Are there any "Awaiting Approval" items in the filtered set?
  const hasAwaiting = useMemo(() => filtered.some(isAwaitingApproval), [filtered]);

  const ordered = useMemo(() => {
    const list = [...filtered];

    if (hasAwaiting) {
      const awaiting = list.filter(isAwaitingApproval);
      const others = list.filter((p) => !isAwaitingApproval(p));
      return [...awaiting, ...others];
    }

    return list.sort((a, b) => {
      const A = getUpdatedAt(a);
      const B = getUpdatedAt(b);
      return sortDir === "asc" ? A - B : B - A;
    });
  }, [filtered, hasAwaiting, sortDir]);

  useEffect(() => {
    const totalItems = ordered.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [ordered.length, pageSize, page]);

  const totalItems = ordered.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIdx = (currentPage - 1) * pageSize;
  const pageItems = ordered.slice(startIdx, startIdx + pageSize);

  const hasActiveSearchOrFilters =
    (canSearch && effectiveQuery.length > 0) || selectedStatuses.length > 0;

  const noItems = totalItems === 0;
  const noResultsForSearch = noItems && hasActiveSearchOrFilters;

  return (
    <div className="bg-bg-content min-h-screen mt-14">
      <div className="max-w-321 mx-auto flex gap-8">
        {/* LEFT */}
        <div className="flex-1 bg-white rounded-md border border-gray-200">
          <div>
            {/* Header row */}
            <div className="flex justify-between items-center mb-6 px-6 pt-6">
              <h2 className="text-2xl font-light text-text-dark">Projects</h2>
            </div>

            {/* Controls Row */}
            <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 sm:gap-3 mb-6 px-6">
              <div className="flex items-center gap-2">
                <SearchInput
                  value={search}
                  onChange={setSearch}
                  placeholder="Search by project or program name"
                  className="w-105"
                />
                <StatusFilter
                  role={role}
                  selected={selectedStatuses}
                  onToggle={toggleStatus}
                  onClearAll={clearAll}
                  className="w-auto "
                />
              </div>

              <div className="ml-auto flex items-center gap-2 ">
                {showRequestAccessButton && (
                  <button
                    className="cursor-pointer h-9 text-sm rounded-[var(--radius-3)] bg-primary px-4 py-1.5 text-white"
                    type="button"
                    onClick={openRequestModal}
                  >
                    Request project access
                  </button>
                )}
                {showProjectCreationButton && (
                  <button
                    className="cursor-pointer h-9 text-sm rounded-[var(--radius-3)] bg-primary px-4 py-1.5 text-white"
                    onClick={() => navigate("/AddNewProject")}
                    type="button"
                  >
                    Create Project
                  </button>
                )}
              </div>
            </div>

            {/* Table / Empty states */}
            <div className="mx-0 px-0">
              {noResultsForSearch ? (
                <div className="px-6 pb-6">
                  <EmptyState
                    title={`No results found for “${effectiveQuery}”`}
                    subtitle="Try searching with a different project or program name. Projects you don’t have access to won’t appear in search results."
                    iconName="search_off"
                  />
                </div>
              ) : (
                <ProjectTable
                  role={role as unknown as string}
                  projects={pageItems}
                  sortDir={sortDir}
                  onSortChange={(dir) => setSortDir(dir)}
                />
              )}
            </div>
          </div>

          {/* Footer-like Pagination bar */}
          {!noItems && (
            <PaginationBar
              page={currentPage}
              totalItems={totalItems}
              pageSize={pageSize}
              onChangePage={setPage}
              onChangePageSize={setPageSize}
            />
          )}
        </div>

        {/* RIGHT COLUMN */}
        <div className="flex flex-col gap-4 w-60 ">
          {/* Awaiting Approval (admin-only) — collapsible */}
          {role !== "user" && (
            <div className="w-59.75 rounded-md border border-info-border/35 bg-info-bg overflow-hidden">
              <button
                type="button"
                className="w-full flex items-center justify-between px-3 py-2.5 text-left cursor-pointer"
                onClick={() => setPendingExpanded((v) => !v)}
              >
                <div className="flex items-center gap-2">
                  <div
                    className="flex items-center justify-center rounded-full bg-info-border flex-shrink-0"
                    style={{ width: 19, height: 19 }}
                  >
                    <span className="material-symbols-rounded text-white" style={{ fontSize: 15 }}>
                      info_i
                    </span>
                  </div>
                  <span className="font-semibold text-sm leading-5 text-info-text">
                    Pending approvals ({pendingApprovals.length})
                  </span>
                </div>
                <span
                  className="material-symbols-rounded text-info-text transition-transform"
                  style={{ fontSize: 18, transform: pendingExpanded ? "rotate(180deg)" : "rotate(0deg)" }}
                >
                  expand_more
                </span>
              </button>

              {pendingExpanded && (
                <div className="border-t border-info-border/15 max-h-56 overflow-y-auto">
                  {pendingApprovals.length === 0 ? (
                    <p className="px-3 py-3 text-xs text-info-text">No pending approvals.</p>
                  ) : (
                    pendingApprovals.map((item) => (
                      <button
                        key={`${item.stage_instance_id}-${item.report_number}`}
                        type="button"
                        className="w-full text-left px-3 py-2 hover:bg-info-border/20 cursor-pointer border-b border-info-border/15 last:border-b-0"
                        onClick={() =>
                          navigate(
                            `/dataEntry?projectId=${item.project_id}&stageInstanceId=${item.stage_instance_id}&reportNumber=${item.report_number}`
                          )
                        }
                      >
                        <div className="font-semibold text-xs text-info-text leading-4 truncate">
                          {item.project_name}
                        </div>
                        <div className="text-xs text-info-text/70 leading-4">
                          {STAGE_LABEL[item.stage] ?? item.stage}
                          {item.num_reports_required > 1 && ` (${item.report_number} of ${item.num_reports_required})`}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          )}

          {/* Reopen Requests (admin-only) — collapsible */}
          {role !== "user" && (
            <div className="w-59.75 rounded-md border border-grey-light bg-white overflow-hidden">
              <button
                type="button"
                className="w-full flex items-center cursor-pointer justify-between px-4 py-3 text-left"
                onClick={() => setReopenExpanded((v) => !v)}
              >
                <span className="font-semibold text-sm text-text-dark leading-5">
                  Pending reopen requests ({pendingReopens.length})
                </span>
                <span
                  className="material-symbols-rounded text-text-faint transition-transform"
                  style={{ fontSize: 18, transform: reopenExpanded ? "rotate(180deg)" : "rotate(0deg)" }}
                >
                  expand_more
                </span>
              </button>

              {reopenExpanded && (
                <div className="border-t border-grey-light/40 max-h-56 overflow-y-auto">
                  {pendingReopens.length === 0 ? (
                    <p className="px-4 py-3 text-xs text-text-faint">No pending reopen requests.</p>
                  ) : (
                    pendingReopens.map((item) => (
                      <button
                        key={`${item.stage_instance_id}-${item.report_number}`}
                        type="button"
                        className="w-full text-left px-4 py-2.5 cursor-pointer hover:bg-neutral-50 cursor-pointer border-b border-color-border last:border-b-0"
                        onClick={() =>
                          navigate(
                            `/dataEntry?projectId=${item.project_id}&stageInstanceId=${item.stage_instance_id}&reportNumber=${item.report_number}`
                          )
                        }
                      >
                        <div className="font-semibold text-xs text-text-dark leading-4 truncate">
                          {item.project_name}
                        </div>
                        <div className="text-xs text-text-faint leading-4">
                          {STAGE_LABEL[item.stage] ?? item.stage}
                          {item.num_reports_required > 1 && ` (${item.report_number} of ${item.num_reports_required})`}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          )}

          <div style={{ width: 239 }}>
            <SummaryCard data={data} />
          </div>
          {role === "Org admin" && (
            <div className="w-full">
              <button
                type="button"
                className="w-full bg-primary text-white rounded-[3px] cursor-pointer px-4 py-3 font-medium text-center"
                onClick={() =>
                  navigate(`/orgResultDashboard?orgId=${user?.organisation_id}`)
                }
              >
                Organisational dashboard
              </button>
            </div>
          )}
        </div>

      </div>

      {/* Request Access Modal */}
      <Modal isOpen={showRequestAccess} onClose={closeRequestModal} className="max-w-150 p-6">
        <ProjectAccess
          onCloseRequestModal={() => {
            closeRequestModal();
          }}
          onOpenCancelModal={() => {
            openCancelModal();
          }}
          onCloseAllModals={() => {
            closeAllModals();
          }}
        />
      </Modal>

      {/* Cancel / Discard Confirmation Modal */}
      <Modal isOpen={showCancelConfirm} onClose={closeCancelModal} className="max-w-150 p-6">
        <div className="bg-white p-2 sm:p-4">
          <div className="text-lg sm:text-2xl text-text-dark font-medium">Discard changes?</div>
          <div className="mt-3 sm:mt-4 text-sm text-text-base">
            Are you sure you want to discard your changes?
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <button
              className="cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 cursor-pointer text-sm font-medium text-text-table-cell transition-colors hover:bg-neutral-95"
              type="button"
              onClick={() => {
                closeCancelModal();
                openRequestModal();
              }}
            >
              Keep editing
            </button>
            <button
              className="cursor-pointer rounded-[var(--radius-3)] border cursor-pointer bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95"
              type="button"
              onClick={closeAllModals}
            >
              Discard changes
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default ProjectsPage;