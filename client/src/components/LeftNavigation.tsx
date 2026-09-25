import { useState, useMemo, useEffect } from 'react';
import type { LeftNavigationProps, SubStageGroup } from '../types/reports';
import { SelectListbox } from './common/Select';

const LeftNavigation = ({
  onSelectReport,
  selectedReportId,
  stageType = "",
  stages,
  onSelectStage,
  // constructionWindow,
  activeSubStage = null,
  onSelectSubStage,
  subStages = [],
  groups = [],
  reportFrequency = "Monthly",
  // firstSubmissionMonth,
  // constructionReportStates = [],
  constructionPeriods,
  projectName,
  activeStageInstance,
  programName,
  activeReportNumber,
  isStageAdmin = false,
  showMitigations = false,
  onSelectMitigations,
  mitigationsTabEnabled = false,
showCompleteness = false,
onSelectCompleteness,
completenessTabEnabled = false,
  hasResubmissionAudit = false,
  onViewResubmissionAudit,
}: LeftNavigationProps) => {
  const [isCollapsed, setIsCollapsed] = useState<Boolean>(false);

  const [submissionDetailsExpanded, setSubmissionDetailsExpanded] = useState<boolean>(true);
  const [reviewerDetailsExpanded, setReviewerDetailsExpanded] = useState<boolean>(true);
  const [quickLinksExpanded, setQuickLinksExpanded] = useState<boolean>(true);


  const submittedBy = activeStageInstance?.submitted_by ?? '—';
  const submittedAt = activeStageInstance?.submitted_at
    ? new Date(activeStageInstance.submitted_at).toLocaleString()
    : 'N/A';


  const PERIOD_STATUS_LABELS: Record<string, string> = {
    in_progress: "In Progress",
    awaiting_approval: "Awaiting Approval",
    approved: "Approved",
    rejected: "Rejected",
    reopen_requested: "Reopen Requested",
  };

  const constructionPeriodOptions = useMemo(() => {
    if (!constructionPeriods || constructionPeriods.length === 0) return [];
    return [...constructionPeriods]
      .sort((a, b) => b.period_start_date.localeCompare(a.period_start_date))
      .map((p) => ({
        value: p.id,
        label: p.period_label,
        status: PERIOD_STATUS_LABELS[p.status] ?? p.status,
      }));
  }, [constructionPeriods]);

  const stageOptions = useMemo(
    () =>
      stages.map((s: any) => ({
        label: s.label ?? s.name,
        value: s.value,
        disabled: s.disabled,
      })),
    [stages]
  );
  
const selectedStageValue = useMemo(() => {
  const match = stages.find(
    (s: any) =>
      s.stageLabel === stageType &&
      (activeReportNumber == null || s.reportNumber === activeReportNumber || s.reportNumber == null)
  );
  return match?.value ?? "";
}, [stages, stageType, activeReportNumber]);

  const isConstruction = stageType === "Construction" || stageType === "Recurring";
  const isDesign = stageType === "Design";
  const showMitigationsTab = mitigationsTabEnabled;
  
 const showCompletenessTab =
    (stageType === "Business case" || isDesign || stageType === "Construction") &&
    completenessTabEnabled;

const isProjAdmin = isStageAdmin;

  useEffect(() => {
    if (
      stageType !== "Construction" ||
      !constructionPeriods?.length ||
      selectedReportId
    ) return;

    // Prefer in-progress period
    const active =
      constructionPeriods.find(p => p.status === "in_progress") ??
      constructionPeriods[0];

    if (active) {
      onSelectReport?.(active.id);
    }
  }, [stageType, constructionPeriods, selectedReportId, onSelectReport]);

  const renderBlocks = useMemo(() => {
    // Block types
    type HeaderBlock = { type: 'header'; key: string; label: string; children: { label: string; value: string }[] };
    type ItemBlock = { type: 'item'; key: string; label: string; value: string };
    const blocks: (HeaderBlock | ItemBlock)[] = [];

    if (!subStages?.length) return blocks;

    // Build a reverse index value -> group
    const groupByValue = new Map<string, SubStageGroup>();
    for (const g of groups ?? []) {
      for (const v of g.childrenValues) groupByValue.set(v, g);
    }

    // Collect children by header, preserving the order from subStages
    const childrenByHeader = new Map<string, { label: string; value: string }[]>();
    for (const item of subStages) {
      const g = groupByValue.get(item.value);
      if (!g) continue;
      const arr = childrenByHeader.get(g.header) ?? [];
      arr.push({ label: item.label, value: item.value });
      childrenByHeader.set(g.header, arr);
    }

    const insertedHeader = new Set<string>();
    for (const item of subStages) {
      const g = groupByValue.get(item.value);
      if (g) {
        if (!insertedHeader.has(g.header)) {
          blocks.push({
            type: 'header',
            key: `header-${g.header}`,
            label: g.header,
            children: childrenByHeader.get(g.header) ?? [],
          });
          insertedHeader.add(g.header);
        }
        continue;
      }
      blocks.push({ type: 'item', key: item.value, label: item.label, value: item.value });
    }

    return blocks;
  }, [subStages, groups]);

  const renderMitigationsTab = () => {
    if (!showMitigationsTab) return null;
    const selected = !!showMitigations;
    return (
      <div className="px-2">
        <button
          type="button"
          onClick={() => onSelectMitigations?.()}
          className={`w-full flex items-center gap-2 text-left px-2 py-2 text-sm cursor-pointer ${
            selected
              ? 'border-l-2 border-primary bg-primary-weak text-primary font-medium'
              : 'border-l-2 border-transparent text-text-base hover:bg-neutral-95'
          }`}
        >
         {/*  <span className="material-symbols-rounded text-[18px]">eco</span> */}
          Mitigations
        </button>
      </div>
    );
  };

  const renderCompletenessTab = () => {
  if (!showCompletenessTab) return null;

  const selected = !!showCompleteness;

  return (
    <div className="px-2">
      <button
        type="button"
        onClick={() => onSelectCompleteness?.()}
        className={`w-full flex items-center gap-2 text-left px-2 py-2 text-sm cursor-pointer ${
          selected
            ? "border-l-2 border-primary bg-primary-weak text-primary font-medium"
            : "border-l-2 border-transparent text-text-base hover:bg-neutral-95"
        }`}
      >
        Completeness
      </button>
    </div>
  );
};

  const renderStageContent = () => {
    if (!isConstruction) {
      return (
        <div className="capitalize text-sm">
          <ul className="flex flex-col gap-1">
            {renderBlocks.map((b) =>
              b.type === 'header' ? (
                <li key={b.key} className="mb-1">
                  <div
                    className="px-2 py-2 rounded-[var(--radius-3)] border-l-2 border-primary border-transparent text-text-faint text-xs font-semibold"
                    role="heading"
                    aria-level={2}
                  >
                    {b.label}
                  </div>
                  {!!b.children.length && (
                    <ul className="ml-4 mt-1 flex flex-col">
                      {b.children.map((child) => {
                        const selected = activeSubStage?.toString().trim() === child.value?.toString().trim();
                        return (
                          <li key={child.value}>
                            <button
                              type="button"
                              onClick={() => onSelectSubStage?.(child.value)}
                              className={`w-full  text-left px-3 py-1.5 cursor-pointer ${selected
                                ? 'border-l-2 border-primary text-primary bg-primary-weak font-medium'
                                : 'border-l-2 text-text-base **:border-transparent hover:bg-neutral-95'
                                }`}
                            >
                              {child.label}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              ) : (
                <li key={b.key}>
                  <button
                    type="button"
                    onClick={() => onSelectSubStage?.(b.value)}
                    className={`w-full text-left px-2 py-2 cursor-pointer ${activeSubStage?.toString().trim() === b.value?.toString().trim()
                      ? 'border-l-2 border-primary bg-primary-weak text-primary font-medium'
                      : 'border-l-2 border-transparent hover:bg-neutral-95 text-text-base'
                      }`}
                  >
                    {b.label}
                  </button>
                </li>
              )
            )}
          </ul>
        </div>
      );

    }
    return (
      <>
        <div className="inline-flex capitalize text-text-base text-sm">
          <span className="material-symbols-rounded w-4 h-4 mr-2 shrink-0" aria-label="Calendar Clock">calendar_clock</span>
          <span>{reportFrequency}</span>
        </div>
        <div className="flex flex-col gap-4 overflow-y-auto hide-scrollbar">

          <SelectListbox
            value={selectedReportId ?? ""}
            onChange={(value: string) => onSelectReport?.(value)}
            options={constructionPeriodOptions}
          />
        </div>
                {subStages.length > 0 && (
          <div className="capitalize text-sm mt-2">
            <ul className="flex flex-col gap-1">
              {renderBlocks.map((b) =>
                b.type === 'header' ? (
                  <li key={b.key} className="mb-1">
                    <div
                      className="px-2 py-2 rounded-[var(--radius-3)] border-l-2 border-primary border-transparent text-text-faint text-xs font-semibold"
                      role="heading"
                      aria-level={2}
                    >
                      {b.label}
                    </div>
                    {!!b.children.length && (
                      <ul className="ml-4 mt-1 flex flex-col">
                        {b.children.map((child) => {
                          const selected = activeSubStage?.toString().trim() === child.value?.toString().trim();
                          return (
                            <li key={child.value}>
                              <button
                                type="button"
                                onClick={() => onSelectSubStage?.(child.value)}
                                className={`w-full text-left px-3 py-1.5  cursor-pointer ${selected
                                  ? 'border-l-2 border-primary text-primary bg-primary-weak font-medium'
                                  : 'border-l-2 text-text-base **:border-transparent hover:bg-neutral-95'
                                  }`}
                              >
                                {child.label}
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </li>
                ) : (
                  <li key={b.key}>
                    <button
                      type="button"
                      onClick={() => onSelectSubStage?.(b.value)}
                      className={`w-full text-left px-2 py-2 cursor-pointer ${activeSubStage?.toString().trim() === b.value?.toString().trim()
                        ? 'border-l-2 border-primary bg-primary-weak text-primary font-medium'
                        : 'border-l-2 border-transparent hover:bg-neutral-95 text-text-base'
                        }`}
                    >
                      {b.label}
                    </button>
                  </li>
                )
              )}
            </ul>
          </div>
        )}

      </>
    )
  }



  if (isCollapsed) {
    return (
      <aside
        className="w-[var(--sidebar-width-collapsed)] h-full bg-white p-6 relative overflow-visible"
        style={{ boxShadow: 'inset -1px 0 0 var(--color-neutral-90)' }}
      >
        <button
          onClick={() => setIsCollapsed(false)}
          className="absolute top-4.5 left-10.5 z-20 text-text-base cursor-pointer border border-light-grey w-9 h-9 bg-white rounded-full shadow-sm hover:bg-neutral-95 transition-colors flex items-center justify-center"
        >
          <span className="material-symbols-rounded w-6 h-6 shrink-0">
            keyboard_double_arrow_right
          </span>
        </button>
      </aside>
    );
  }


  // Expanded view — Admin vs Non-admin
  return (
    <aside className="w-[var(--sidebar-width)] h-full border-r border-neutral-90 bg-white p-6 relative overflow-y-auto">
      <nav className="flex flex-col gap-4 h-full">
        <div className="sticky top-0 bg-white z-10 flex flex-col gap-4 pb-4">
          {/* Header (title + collapse) varies by role */}
          <div className="flex justify-between items-center font-medium border-b border-neutral-95 text-text-dark">
            <span>
              {isProjAdmin ? (
                'Submission for approval'
              ) : (
                <>
                  Reports {isConstruction ? `(${constructionPeriodOptions.length})` : null}
                </>
              )}
            </span>
            <button
              onClick={() => setIsCollapsed(true)}
              className="text-text-base hover:bg-neutral-95 p-1 rounded transition-colors cursor-pointer"
            >
              <span className="material-symbols-rounded w-5 h-5 mr-2 shrink-0">
                keyboard_double_arrow_left
              </span>
            </button>
          </div>

          {/* ===================== ADMIN VIEW ===================== */}
          {isProjAdmin ? (
            <>
              {/* Status & project summary (match your mock) */}


              {stages.length > 1 && (
                <SelectListbox
                  value={selectedStageValue}
                  onChange={(value: any) => onSelectStage?.(value)}
                  options={stages}
                />
              )}
              <div
                className={`w-fit text-sm px-4 py-1 rounded-full ${activeStageInstance?.approval_status === "draft"
                  ? "bg-[#EEE8F8] text-[#5A3A80]"
                  : activeStageInstance?.approval_status === "pending_reopen"
                    ? "bg-[#9EF0F0] text-[#005D5D]"
                    : activeStageInstance?.approval_status === "submitted"
                      ? "bg-[#EEE8F8] text-[#5A3A80]"
                      : activeStageInstance?.approval_status === "rejected"
                        ? "bg-danger/35 text-danger"
                        : activeStageInstance?.approval_status === "final_approved"
                          ? "bg-light-green text-success"
                          : "text-text-base"
                  }`}
              >
                {/* {activeStageInstance?.approval_status?.replace("_", " ")} */}
                {activeStageInstance?.approval_status === "draft" ? "In Progress"
                  : activeStageInstance?.approval_status === "submitted" ? "Awaiting Approval"
                    : activeStageInstance?.approval_status === 'pending_reopen' ? "Reopen Requested"
                      : activeStageInstance?.approval_status?.replace("_", " ") ?? "In Progress"}
              </div>
              <div className="text-base text-text-dark font-medium">{stageType}</div>
              <div className="text-text-table-cell">
                {projectName}
                <div className="text-xs text-text-faint">
                  {programName}
                </div>
              </div>



              {/* Submission details (collapsible) */}
              {activeStageInstance?.approval_status === "submitted" && (
                <div className="bg-white p-2">
                  <div className="flex items-center justify-between py-4">
                    <span className="font-medium text-text-dark">Submission details</span>
                    <button
                      type="button"
                      onClick={() => setSubmissionDetailsExpanded(v => !v)}
                      className="w-5 h-5 inline-flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded cursor-pointer"
                      aria-expanded={submissionDetailsExpanded}
                      aria-controls="submission-details-panel"
                    >
                      <span className="material-symbols-rounded">
                        {submissionDetailsExpanded ? 'keyboard_arrow_up' : 'keyboard_arrow_down'}
                      </span>
                    </button>
                  </div>

                  <div id="submission-details-panel" className={submissionDetailsExpanded ? 'block' : 'hidden'}>
                    <div className="bg-neutral-95 my-4 p-4 rounded-[var(--radius-3)]">
                      <div className="text-xs text-text-faint uppercase mb-2">SUBMITTED BY</div>
                      <div className="text-text-table-cell">{submittedBy}</div>
                    </div>
                    <div className="bg-neutral-95 mb-4 p-4 rounded-[var(--radius-3)]">
                      <div className="text-xs text-text-faint uppercase mb-2">Date submitted</div>
                      <div className="text-text-table-cell">{submittedAt}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Quick links (collapsible) */}
              <div className="bg-white px-2 pt-2">
                <div className="flex items-center justify-between py-4">
                  <span className="font-medium text-text-dark">Quick links</span>
                  <button
                    type="button"
                    onClick={() => setQuickLinksExpanded(prev => !prev)}
                    className="w-5 h-5 inline-flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded cursor-pointer"
                    aria-expanded={quickLinksExpanded}
                    aria-controls="quick-links-panel"
                  >
                    <span className="material-symbols-rounded">
                      {quickLinksExpanded ? 'keyboard_arrow_up' : 'keyboard_arrow_down'}
                    </span>
                  </button>
                </div>

                <div id="quick-links-panel" className={quickLinksExpanded ? 'block' : 'hidden'}>
                  {renderStageContent()}
                </div>
              </div>
              {renderMitigationsTab()}
              {renderCompletenessTab()}
              {hasResubmissionAudit && onViewResubmissionAudit && (
                <div className="px-2 pt-3 pb-1 border-t border-neutral-90 mt-2">
                  <button
                    type="button"
                    onClick={onViewResubmissionAudit}
                    className="w-full flex items-center gap-2 px-2 py-2 text-sm text-primary cursor-pointer hover:bg-primary-weak rounded transition-colors border-l-2 border-transparent hover:border-primary"
                  >
                    <span className="material-symbols-rounded text-[18px] shrink-0">history</span>
                    Audit Changes
                  </button>
                </div>
              )}
            </>
          ) : (
            /* ===================== NON-ADMIN VIEW ===================== */
            <>
              {stageOptions.length > 1 && (
                <SelectListbox
                  value={selectedStageValue}
                  onChange={(value: any) => onSelectStage?.(value)}
                  options={stageOptions}
                />
              )}
               {(activeStageInstance?.approval_status === "final_approved" || activeStageInstance?.approval_status === "rejected") && (
                <div className="bg-white p-2">
                  <div className="flex items-center justify-between py-4">
                    <span className="font-medium text-text-dark">Reviewer details</span>
                    <button
                      type="button"
                      onClick={() => setReviewerDetailsExpanded(v => !v)}
                      className="w-5 h-5 inline-flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded cursor-pointer" 
                      aria-expanded={reviewerDetailsExpanded}
                      aria-controls="reviewer-details-panel"
                    >
                      <span className="material-symbols-rounded">
                        {reviewerDetailsExpanded ? 'keyboard_arrow_up' : 'keyboard_arrow_down'}
                      </span>
                    </button>
                  </div>

                  <div id="submission-details-panel" className={reviewerDetailsExpanded ? 'block' : 'hidden'}>
                    <div className="bg-neutral-95 my-4 p-4 rounded-[var(--radius-3)]">
                      <div className="text-xs text-text-faint uppercase mb-2">REVIEWED BY</div>
                      <div className="text-text-table-cell">{activeStageInstance?.approved_by}</div>
                    </div>
                    <div className="bg-neutral-95 mb-4 p-4 rounded-[var(--radius-3)]">
                      <div className="text-xs text-text-faint uppercase mb-2">Date reviewed</div>
                      <div className="text-text-table-cell">{activeStageInstance?.approved_at}</div>
                    </div>
                  </div>
                </div>
              )}


              {renderStageContent()}
              {renderMitigationsTab()}
              {renderCompletenessTab()}
            </>
          )}
        </div>
      </nav>
    </aside>
  );
};



export default LeftNavigation;