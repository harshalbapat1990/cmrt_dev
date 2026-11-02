import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  getMitigationPanelBaseKeys,
  type MitigationPanelBaseKey,
  type MitigationSubstitutionLeg,
} from "./mitigationConstants";
import type { DataEntryRow } from "./dataEntryTypes";
import type { MitigationInlineCellChangeFactory, MitigationInlineRowPatchFactory } from "./mitigationInlineEditHandlers";
import { MITIGATION_LIFECYCLE_PHASE_LABEL as LIFECYCLE_PHASE_LABEL } from "./mitigationTypes";
import type { Mitigation, MitigationLifecyclePhase } from "./mitigationTypes";
import type { UploadKey } from "./stageConstants";
export type { Mitigation, MitigationLifecyclePhase, MitigationType } from "./mitigationTypes";
import { MitigationSummaryView, MitigationsList } from "./components/MitigationOverview";
import { Step1Modal, type Step1Form } from "./components/MitigationStepOne";
import { Step2Modal, type TablePanelRenderOptions } from "./components/MitigationStepTwo";
import { EmptyMitigationTables } from "./components/MitigationTableEditor";

/** Wizard collects either one table map (reduction) or replaced/adopted maps (substitution). */
export type MitigationWizardSnapshot =
  | { mode: "reduction"; tables: Record<string, DataEntryRow[]> }
  | {
      mode: "substitution";
      replaced: Record<string, DataEntryRow[]>;
      adopted: Record<string, DataEntryRow[]>;
    };

/** Hydration payload when opening an existing mitigation in the wizard. */
export type MitigationHydrate =
  | { kind: "reduction"; tables: Record<string, DataEntryRow[]> }
  | {
      kind: "substitution";
      replaced: Record<string, DataEntryRow[]>;
      adopted: Record<string, DataEntryRow[]>;
    };

export type MitigationPersistenceApi = {
  saveMitigationBulkTable: (
    baseKey: MitigationPanelBaseKey,
    projectMitigationId: string,
    rows: DataEntryRow[],
    substitutionLeg?: MitigationSubstitutionLeg | null,
  ) => Promise<void>;
  loadMitigationTable: (
    baseKey: MitigationPanelBaseKey,
    projectMitigationId: string,
    substitutionLeg?: MitigationSubstitutionLeg | null,
  ) => Promise<DataEntryRow[]>;
  patchMitigationMeta: (
    projectMitigationId: string,
    meta: {
      name: string;
      type: string;
      lifecyclePhase: string;
      lifecyclePhaseLabel: string;
      notes?: string;
      group?: string;
      submissionStage: string;
    },
  ) => Promise<void>;
  createMitigation: (meta: {
    name: string;
    type: string;
    lifecyclePhase: string;
    lifecyclePhaseLabel: string;
    notes?: string;
    group?: string;
    submissionStage: string;
  }) => Promise<string>;
  loadMitigationsForStage: (submissionStageFilter: string) => Promise<
    Array<{
      mitigationId: string;
      name: string;
      type: string;
      lifecyclePhase: string;
      lifecyclePhaseLabel: string;
      notes?: string;
      group?: string;
      submissionStage: string;
    }>
  >;
  deleteMitigation: (projectMitigationId: string) => Promise<void>;
  saveMitigationNewRow: (
    tableKey: UploadKey,
    projectMitigationId: string,
    draft: DataEntryRow,
    appendRow: (tk: string, row: DataEntryRow) => void,
    setTableError: (msg: string | null) => void,
    substitutionLeg?: MitigationSubstitutionLeg | null,
  ) => Promise<boolean>;
  /** Shared emission calculators from DataEntry (incl. mitigation concrete in activity_data). */
  computeEmissionsForRow?: (
    tableKey: string,
    row: DataEntryRow,
  ) => Promise<Partial<DataEntryRow> | null>;
  refreshOptionTotals?: () => Promise<void>;
   /** Inline cell edit with local recalc (no immediate API persist). */
  onCellChange?: MitigationInlineCellChangeFactory;
  onRowPatch?: MitigationInlineRowPatchFactory;
  /** Bulk upload rows from CSV/XLSX into mitigation-scoped activity_data (same enrichment as main upload). */
  uploadMitigationTableFile?: (
    baseKey: UploadKey,
    projectMitigationId: string,
    parsedValidRows: DataEntryRow[],
    substitutionLeg?: MitigationSubstitutionLeg | null,
  ) => Promise<{ rows: DataEntryRow[] }>;
};

export type MitigationTablesCollector = {
  collect: () => Record<string, DataEntryRow[]>;
};



export type StageName = "Design" | "Construction";

type MitigationsProps = {
  stage: StageName;
  projectId: string;
  jurisdictionName?: string | null;
  canSubmit?: boolean;
  onSubmitStage?: () => void;
  onNextStage?: () => void;
  /** When true (Australia completeness flow), footer advances to Completeness instead of submitting. */
  useCompletenessSubmissionFlow?: boolean;
  persistence: MitigationPersistenceApi | null;
  editorLocked: boolean;
  isSubmitted: boolean;
  /** Design/Construction stage instance used for mitigation-scoped activity_data (not main nav stage). */
  mitigationStageInstanceId?: string | null;
  mitigationProjectOptionId?: string | null;
  projectTypeName?: string | null;
  opsStartYear?: number | null;
};

/**
 * Lightweight editor used inside mitigation tables. Mirrors the basic editor
 patterns used by the main DataEntry page. Inline edits recalc emissions
 * locally on blur; persistence happens on mitigation modal Save.
 */
const sumRowsEmissions = (rows: DataEntryRow[]): number =>
  rows.reduce((acc, row) => {
    const v = Number(row.total_emissions_tco2e ?? row.emissions_tco2e ?? 0);
    return acc + (Number.isFinite(v) ? v : 0);
  }, 0);

function rowContributionUsersMitigation(row: DataEntryRow): number {
  const direct = Number(row.total_emissions_tco2e ?? row.emissions_tco2e);
  if (Number.isFinite(direct) && direct !== 0) {
    return Math.abs(direct);
  }
  const m = { ...(row?.extra_fields && typeof row.extra_fields === "object" ? row.extra_fields : {}), ...row };
  const candidates = [
    m.interim_total_tco2e,
    m.absoluteEmissions,
    m.absolute_emissions,
    m.absolute_emissions_tco2e,
    m.interim_absolute_emissions_tco2e,
    m.final_user_emissions_tco2e,
    m.relativeUserEmissions,
    m.relative_user_emissions,
    m.emissions_total_ref_period_tco2e,
    m.emissions_annual_tco2e,
  ];
  for (const c of candidates) {
    const n = Number(c);
    if (Number.isFinite(n)) {
      return Math.abs(n);
    }
  }
  return 0;
}

function sumUsersMitigationRowsEmissions(rows: DataEntryRow[]): number {
  return rows.reduce((acc, row) => acc + rowContributionUsersMitigation(row), 0);
}

/**
 * Empty data-entry tables mirroring the main workflow. Rows are local-only.
 * Filtered by lifecycle phase (Construction vs Operations & Maintenance vs Users),
 * then by submission stage (Design vs Construction).
 */
const Mitigations: React.FC<MitigationsProps> = ({
  stage,
  projectId,
  jurisdictionName,
  canSubmit = true,
  onSubmitStage,
  onNextStage,
  useCompletenessSubmissionFlow = false,
  persistence,
  editorLocked,
  isSubmitted,
  mitigationStageInstanceId = null,
  mitigationProjectOptionId = null,
  projectTypeName = null,
  opsStartYear = null,
}) => {
  const [mitigations, setMitigations] = useState<Mitigation[]>([]);
  const [summaryAccordionOpen, setSummaryAccordionOpen] = useState(false);
  const [tableAccordionOpen, setTableAccordionOpen] = useState(true);
  const [step1Open, setStep1Open] = useState(false);
  const [draft, setDraft] = useState<Step1Form | null>(null);
  const [step2Open, setStep2Open] = useState(false);
  const [wizardScenarioId, setWizardScenarioId] = useState<string | null>(null);
  const [hydrateSnapshot, setHydrateSnapshot] = useState<MitigationHydrate | null>(
    null,
  );
  const [detailReadOnly, setDetailReadOnly] = useState(false);
  const tablesCollectorRef = useRef<{
    collect: () => MitigationWizardSnapshot;
  } | null>(null);
  const navigate = useNavigate();

  const closeStep1Modal = useCallback(() => {
    setStep1Open(false);
  }, []);

  const refreshMitigations = useCallback(async () => {
    if (!persistence) return;
    try {
      const rows = await persistence.loadMitigationsForStage(stage);
      const mapped: Mitigation[] = await Promise.all(
        rows.map(async (r) => {
          const keys = getMitigationPanelBaseKeys(
            stage,
            r.lifecyclePhase as MitigationLifecyclePhase,
          );
          const lc = r.lifecyclePhase as MitigationLifecyclePhase;
          const sumTableRows = (tableRows: DataEntryRow[]) =>
            lc === "users"
              ? sumUsersMitigationRowsEmissions(tableRows)
              : sumRowsEmissions(tableRows);
          let estimatedSavingTco2e = 0;
          try {
            if (r.type === "substitution") {
              let totalReplaced = 0;
              let totalAdopted = 0;
              for (const k of keys) {
                try {
                  const replacedRows = await persistence.loadMitigationTable(
                    k,
                    r.mitigationId,
                    "replaced",
                  );
                  const adoptedRows = await persistence.loadMitigationTable(
                    k,
                    r.mitigationId,
                    "adopted",
                  );
                  totalReplaced += sumTableRows(replacedRows);
                  // "Source(s) adopted" in the UI — treated as avoided emissions for the formula.
                  totalAdopted += sumTableRows(adoptedRows);
                } catch (tableErr) {
                  console.warn(
                    "[Mitigations] Skipping substitution leg for landing row:",
                    r.mitigationId,
                    k,
                    tableErr,
                  );
                }
              }
              estimatedSavingTco2e = Math.abs(totalReplaced - totalAdopted);
            } else {
              let sumAcrossTables = 0;
              for (const k of keys) {
                try {
                  const trows = await persistence.loadMitigationTable(
                    k,
                    r.mitigationId,
                  );
                  sumAcrossTables += sumTableRows(trows);
                } catch (tableErr) {
                  console.warn(
                    "[Mitigations] Skipping panel emissions for landing row (table load failed):",
                    r.mitigationId,
                    k,
                    tableErr,
                  );
                }
              }
              estimatedSavingTco2e = sumAcrossTables;
            }
          } catch (aggErr) {
            console.warn(
              "[Mitigations] Emissions aggregation failed for landing row:",
              r.mitigationId,
              aggErr,
            );
          }
          return {
            id: r.mitigationId,
            name: r.name,
            type: r.type === "substitution" ? "substitution" : "reduction",
            group: r.group,
            notes: r.notes,
            lifecyclePhase: r.lifecyclePhase as MitigationLifecyclePhase,
            lifecyclePhaseLabel: r.lifecyclePhaseLabel,
            estimatedSavingTco2e,
          };
        }),
      );
      setMitigations(mapped);
    } catch (e) {
      console.warn("Failed to load mitigations:", e);
    }
  }, [persistence, stage]);

  useEffect(() => {
    void refreshMitigations();
  }, [refreshMitigations]);

  const openMitigationDetail = async (
    m: Mitigation,
    readOnly: boolean,
  ) => {
    if (!persistence) return;
    const lc = m.lifecyclePhase;
    const keys = getMitigationPanelBaseKeys(stage, lc);
    if (m.type === "substitution") {
      const replaced: Record<string, DataEntryRow[]> = {};
      const adopted: Record<string, DataEntryRow[]> = {};
      for (const k of keys) {
        replaced[k] = await persistence.loadMitigationTable(
          k,
          m.id,
          "replaced",
        );
        adopted[k] = await persistence.loadMitigationTable(
          k,
          m.id,
          "adopted",
        );
      }
      setHydrateSnapshot({ kind: "substitution", replaced, adopted });
    } else {
      const tables: Record<string, DataEntryRow[]> = {};
      for (const k of keys) {
        tables[k] = await persistence.loadMitigationTable(k, m.id);
      }
      setHydrateSnapshot({ kind: "reduction", tables });
    }
    setDraft({
      name: m.name,
      type: m.type,
      group: m.group ?? "",
      notes: m.notes ?? "",
      lifecyclePhase: lc,
    });
    setWizardScenarioId(m.id);
    setDetailReadOnly(readOnly);
    setStep2Open(true);
  };

  const handleAdd = () => {
    if (!canSubmit) return;
    setDetailReadOnly(false);
    setDraft(null);
    setWizardScenarioId(null);
    setHydrateSnapshot(null);
    setStep1Open(true);
  };

  const handleStep1Next = async (form: Step1Form) => {
    if (!canSubmit || !persistence?.createMitigation) return;
    setDetailReadOnly(false);
    const id = await persistence.createMitigation({
      name: form.name,
      type: form.type || "reduction",
      lifecyclePhase: form.lifecyclePhase as string,
      lifecyclePhaseLabel:
        LIFECYCLE_PHASE_LABEL[form.lifecyclePhase as MitigationLifecyclePhase],
      notes: form.notes?.trim(),
      group: form.group?.trim(),
      submissionStage: stage,
    });
    setDraft(form);
    setWizardScenarioId(id);
    setHydrateSnapshot(null);
    setStep1Open(false);
    setStep2Open(true);
  };

  const handleStep2Close = useCallback(() => {
    setStep2Open(false);
    setDraft(null);
    setWizardScenarioId(null);
    setHydrateSnapshot(null);
    setDetailReadOnly(false);
  }, []);

  const handleEdit = (m: Mitigation) => {
    if (!canSubmit || editorLocked) return;
    void openMitigationDetail(m, false);
  };

  const handleDelete = async (id: string) => {
    if (!persistence || editorLocked) return;
    try {
      await persistence.deleteMitigation(id);
      await refreshMitigations();
    } catch (e) {
      console.warn("Failed to delete mitigation:", e);
    }
  };

  const handleExit = () => {
    navigate(`/projects/${projectId}`);
  };

  const handleSubmitProject = () => {
    if (!canSubmit || editorLocked) return;
    onSubmitStage?.();
  };

  const handlePrimaryFooterAction = () => {
    if (useCompletenessSubmissionFlow) {
      onNextStage?.();
      return;
    }
    if (!canSubmit || editorLocked) return;
    handleSubmitProject();
  };

  const allowLandingMutations = canSubmit && !editorLocked;
  const submitDisabled = !canSubmit || editorLocked || isSubmitted;
  const primaryFooterLabel = useCompletenessSubmissionFlow
    ? "Next"
    : "Submit";

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-neutral-98">
       <div className="flex-1 overflow-y-auto min-h-0 pb-8">
        <div className="space-y-8 mx-12 mt-8 mb-12">
          <div className="bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)] space-y-8">
            <div className="flex items-center justify-between">
              <div className="text-2xl font-light text-text-dark">
                Mitigations Summary
              </div>
              <button
                type="button"
                aria-expanded={summaryAccordionOpen}
                onClick={() =>
                  setSummaryAccordionOpen((prev) => !prev)
                }
                className="w-5 h-5 inline-flex items-center justify-center cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary rounded"
              >
                <span className="material-symbols-rounded">
                  {summaryAccordionOpen
                    ? "keyboard_arrow_up"
                    : "keyboard_arrow_down"}
                </span>
              </button>
            </div>
            {summaryAccordionOpen && (
              <MitigationSummaryView
                embedded
                mitigations={mitigations}
              />
            )}
          </div>

          <div className="bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)] space-y-8">
            <div className="flex items-center justify-between">
              <div className="text-2xl font-light text-text-dark">
                Mitigations
              </div>
              <button
                type="button"
                aria-expanded={tableAccordionOpen}
                onClick={() =>
                  setTableAccordionOpen((prev) => !prev)
                }
                className="w-5 h-5 inline-flex items-center cursor-pointer justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded"
              >
                <span className="material-symbols-rounded">
                  {tableAccordionOpen
                    ? "keyboard_arrow_up"
                    : "keyboard_arrow_down"}
                </span>
              </button>
            </div>
            {tableAccordionOpen && (
              <MitigationsList
                embedded
                mitigations={mitigations}
                onAdd={handleAdd}
                onDelete={handleDelete}
                onEdit={handleEdit}
                allowMutations={allowLandingMutations}
                viewOnlyInteraction={editorLocked}
                onOpenRow={(m) => {
                  void openMitigationDetail(m, true);
                }}
              />
            )}
          </div>
        </div>
      </div>

      <Step1Modal
        isOpen={step1Open}
        onClose={closeStep1Modal}
        onNext={handleStep1Next}
        submissionStage={stage}
      />

      <Step2Modal
        isOpen={step2Open}
        onClose={handleStep2Close}
        draft={draft}
        submissionStage={stage}
        mitigationScenarioId={wizardScenarioId}
        persistence={persistence}
        hydrateSnapshot={hydrateSnapshot}
        detailReadOnly={detailReadOnly}
        tablesCollectorRef={tablesCollectorRef}
        onPersisted={refreshMitigations}
        renderTables={(options: TablePanelRenderOptions) => {
          if (!draft?.lifecyclePhase) return null;
          return (
            <EmptyMitigationTables
              submissionStage={stage}
              lifecyclePhase={draft.lifecyclePhase as MitigationLifecyclePhase}
              projectId={projectId}
              jurisdictionName={jurisdictionName}
              scopeKey={options.scopeKey}
              collectorRef={options.collectorRef}
              hydrateTables={options.hydrateTables}
              readOnly={detailReadOnly}
              projectMitigationId={wizardScenarioId}
              saveMitigationNewRow={persistence?.saveMitigationNewRow}
              mitigationMode={draft.type === "substitution" ? "substitution" : "reduction"}
              substitutionLeg={options.leg}
              computeEmissionsForRow={persistence?.computeEmissionsForRow}
              onCellChange={persistence?.onCellChange}
              onRowPatch={persistence?.onRowPatch}
              refreshOptionTotals={persistence?.refreshOptionTotals}
              uploadMitigationTableFile={persistence?.uploadMitigationTableFile}
              mitigationStageInstanceId={mitigationStageInstanceId}
              mitigationProjectOptionId={mitigationProjectOptionId}
              projectTypeName={projectTypeName}
              opsStartYear={opsStartYear}
            />
          );
        }}
      />

      <div className="bg-white p-5 px-12 flex justify-end gap-3 border-t border-neutral-90 shrink-0 z-20">
        <button
          className="border border-primary text-primary px-6 py-3 cursor-pointer  rounded-[var(--radius-3)] text-sm font-medium hover:bg-primary/5 transition-colors"
          type="button"
          onClick={handleExit}
        >
          Exit and continue later
        </button>

        <button
          onClick={handlePrimaryFooterAction}
          disabled={!useCompletenessSubmissionFlow && submitDisabled}
          className="bg-primary text-white px-6 py-3 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-opacity-90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          type="button"
        >
         {primaryFooterLabel}
        </button>
      </div>
    </div>
  );
};

export default Mitigations;
