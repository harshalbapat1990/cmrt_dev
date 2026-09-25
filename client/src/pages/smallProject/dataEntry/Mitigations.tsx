import React, {
  useMemo,
  useState,
  useEffect,
  useLayoutEffect,
  useCallback,
  useRef,
} from "react";
import { Modal } from "@/components/common/Modal";
import { SelectListbox } from "@/components/common/Select";
import { NumericInput } from "@/components/common/NumericInput";
import TableWrapper from "@/components/common/TableWrapper";
import { UploadModal } from "@/pages/dummy-table/UploadModal";
import { parseFileToRows } from "@/utils/parseFileToRows";
import { normalizeValidationRules, validateRows } from "@/utils/ValidateRows";
import SteppedProgressBar from "@/components/common/SteppedProgressBar";
import { componentTableConfig } from "./componentConfig";
import { componentReplacementConfig } from "./componentReplacementConfig";
import { refurbishmentTableConfig } from "./refurbishmentTableConfig";
import { opEnergyTableConfig } from "./opEnergyTableConfig";
import { constructionG2Config } from "./constructionG2Config";
import { constructionG3Config } from "./constructionG3Config";
import { electricityConfig } from "./electricityConfig";
import { useB1G2Config } from "./useB1G2Config";
import { useB1G3Config } from "./useB1G3Config";
import { concreteRegSimplifiedConfig } from "./ConcreteRegSimplifiedConfig";
import { useNavigate } from "react-router-dom";
import {
  getMitigationPanelBaseKeys,
  type MitigationSubstitutionLeg,
} from "./mitigationConstants";
import { isElectricityTable } from "./stageConstants";
import ActivityDataService from "@/services/ActivityData.service";
import { useLargeUserYears } from "./hooks/useLargeUserYears";
import UsersSubStage from "./UsersSubStage";
import type {
  MitigationInlineCellChangeFactory,
  MitigationInlineRowPatchFactory,
} from "./mitigationInlineEditHandlers";

type MitigationUploadKey = React.ComponentProps<typeof TableWrapper>["uploadKey"];

function resolveMitigationUploadConfig(uploadKey: MitigationUploadKey, projectId: string) {
  switch (uploadKey) {
    case "component":
      return componentTableConfig(projectId);
    case "bcDetailedLevel":
      return constructionG3Config(projectId);
    case "electricity":
      return electricityConfig(projectId);
    case "concreteRegSimplified":
      return concreteRegSimplifiedConfig();
    case "constructionG2":
      return constructionG2Config(projectId);
    case "constructionG3":
      return constructionG3Config(projectId);
    case "useB1G2":
      return useB1G2Config(null, projectId);
    case "useB1G3":
      return useB1G3Config(projectId);
    case "componentRepl":
      return componentReplacementConfig(projectId);
    case "refurbishment":
      return refurbishmentTableConfig(null);
    case "replDetailed":
      return useB1G3Config(projectId);
    case "opEnergy":
      return opEnergyTableConfig(projectId);
    case "opEnergyDetailed":
      return useB1G3Config(projectId, ["Fuels", "Water"]);
    case "opEnergyElectricity":
      return electricityConfig(projectId);
    default:
      throw new Error(`Unsupported mitigation upload key: ${uploadKey}`);
  }
}

/** Wizard collects either one table map (reduction) or replaced/adopted maps (substitution). */
export type MitigationWizardSnapshot =
  | { mode: "reduction"; tables: Record<string, any[]> }
  | {
      mode: "substitution";
      replaced: Record<string, any[]>;
      adopted: Record<string, any[]>;
    };

/** Hydration payload when opening an existing mitigation in the wizard. */
export type MitigationHydrate =
  | { kind: "reduction"; tables: Record<string, any[]> }
  | {
      kind: "substitution";
      replaced: Record<string, any[]>;
      adopted: Record<string, any[]>;
    };

export type MitigationPersistenceApi = {
  saveMitigationBulkTable: (
    baseKey: string,
    projectMitigationId: string,
    rows: any[],
    substitutionLeg?: MitigationSubstitutionLeg | null,
  ) => Promise<void>;
  loadMitigationTable: (
    baseKey: string,
    projectMitigationId: string,
    substitutionLeg?: MitigationSubstitutionLeg | null,
  ) => Promise<any[]>;
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
    tableKey: string,
    projectMitigationId: string,
    draft: any,
    appendRow: (tk: string, row: any) => void,
    setTableError: (msg: string | null) => void,
    substitutionLeg?: MitigationSubstitutionLeg | null,
  ) => Promise<boolean>;
  /** Shared emission calculators from DataEntry (incl. mitigation concrete in activity_data). */
  computeEmissionsForRow?: (
    tableKey: string,
    row: any,
  ) => Promise<Partial<any> | null>;
  refreshOptionTotals?: () => Promise<void>;
   /** Inline cell edit with local recalc (no immediate API persist). */
  onCellChange?: MitigationInlineCellChangeFactory;
  onRowPatch?: MitigationInlineRowPatchFactory;
  /** Bulk upload rows from CSV/XLSX into mitigation-scoped activity_data (same enrichment as main upload). */
  uploadMitigationTableFile?: (
    baseKey: string,
    projectMitigationId: string,
    parsedValidRows: any[],
    substitutionLeg?: MitigationSubstitutionLeg | null,
  ) => Promise<{ rows: any[] }>;
};

export type MitigationTablesCollector = {
  collect: () => Record<string, any[]>;
};



type StageName = "Design" | "Construction";

/** Lifecycle grouping from left navigation (not the submission-stage dropdown). */
export type MitigationLifecyclePhase =
  | "construction"
  | "operations_maintenance"
  | "users";

const LIFECYCLE_PHASE_OPTIONS: {
  label: string;
  value: MitigationLifecyclePhase;
}[] = [
  { label: "Construction", value: "construction" },
  { label: "Operations & Maintenance", value: "operations_maintenance" },
  { label: "Users", value: "users" },
];

const LIFECYCLE_PHASE_LABEL: Record<MitigationLifecyclePhase, string> = {
  construction: "Construction",
  operations_maintenance: "Operations & Maintenance",
  users: "Users",
};

export type MitigationType = "reduction" | "substitution";

export interface Mitigation {
  id: string;
  name: string;
  type: MitigationType;
  group?: string;
  notes?: string;
  estimatedSavingTco2e: number;
  lifecyclePhase: MitigationLifecyclePhase;
  lifecyclePhaseLabel: string;
}

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

type Step1Form = {
  name: string;
  type: MitigationType | "";
  group: string;
  notes: string;
  lifecyclePhase: MitigationLifecyclePhase | "";
};

const TYPE_OPTIONS = [
  { label: "Avoidance/Reduction Initiative", value: "reduction" },
  { label: "Substitution Initiative", value: "substitution" },
];

const TYPE_LABEL: Record<MitigationType, string> = {
  reduction: "Avoidance/Reduction Initiative",
  substitution: "Substitution Initiative",
};

/**
 * Lightweight editor used inside mitigation tables. Mirrors the basic editor
 patterns used by the main DataEntry page. Inline edits recalc emissions
 * locally on blur; persistence happens on mitigation modal Save.
 */
const MitigationCellEditor = (col: any, props: any) => {
  if (col.editorType === "year") {
    return (
      <input
        type="number"
        className="h-10 w-full bg-white border border-border-input rounded px-2 py-1 text-sm"
        value={props.value ?? ""}
        onChange={(e) => props.onChange(e.target.value)}
        onBlur={() => props.onCommit(props.value)}
        autoFocus
        onKeyDown={(e) => {
          if (e.key === "." || e.key === ",") e.preventDefault();
        }}
      />
    );
  }
  if (col.editorType === "number") {
    return (
      <NumericInput
        value={props.value}
        onChange={props.onChange}
        onCommit={props.onCommit}
        allowDecimal
        autoFocus
        uncontrolled
      />
    );
  }
  if (col.key === "notes") {
    return (
      <input
        className="h-10 w-full bg-white border border-border-input rounded px-2 py-1 text-sm"
        value={props.value ?? ""}
        onChange={(e) => props.onChange(e.target.value)}
        onBlur={() => props.onCommit(props.value)}
        autoFocus
      />
    );
  }
  return col.renderEditor?.(props);
};

const Step1Modal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onNext: (form: Step1Form) => void | Promise<void>;
  submissionStage: StageName;
}> = ({ isOpen, onClose, onNext, submissionStage }) => {
  const [form, setForm] = useState<Step1Form>({
    name: "",
    type: "",
    group: "",
    notes: "",
    lifecyclePhase: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const lifecyclePhaseOptions = useMemo(
    () =>
      submissionStage === "Construction"
        ? LIFECYCLE_PHASE_OPTIONS.filter((o) => o.value !== "users")
        : LIFECYCLE_PHASE_OPTIONS,
    [submissionStage],
  );

  useEffect(() => {
    if (!isOpen) return;
    setForm((f) =>
      f.lifecyclePhase === "users" && submissionStage === "Construction"
        ? { ...f, lifecyclePhase: "" }
        : f,
    );
  }, [isOpen, submissionStage]);

  const handleNext = async () => {
    if (!form.name.trim()) {
      setError("Mitigation name is required.");
      return;
    }
    if (!form.lifecyclePhase) {
      setError("Project stage is required.");
      return;
    }
    if (!form.type) {
      setError("Mitigation type is required.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await onNext(form);
      setForm({
        name: "",
        type: "",
        group: "",
        notes: "",
        lifecyclePhase: "",
      });
    } catch (e) {
      console.warn("Mitigation draft create failed:", e);
      setError("Could not create mitigation. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const handleClose = useCallback(() => {
    setError(null);
    setForm({
      name: "",
      type: "",
      group: "",
      notes: "",
      lifecyclePhase: "",
    });
    onClose();
  }, [onClose]);

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="New mitigation" className="max-w-lg">
      <div className="px-6 pt-6 pb-2">
        <div className="text-2xl text-text-dark mb-1">New mitigation</div>
        {/* <div className="text-sm text-text-faint mb-6">
          Provide the basic information for this custom mitigation.
        </div> */}

        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-text-base mb-1">
              Name <span className="text-danger">*</span>
            </label>
            <input
              className="w-full h-10 bg-white border border-border-input rounded-[var(--radius-3)] px-3 text-sm"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Replace concrete with timber"
            />
          </div>

          <div>
            <label className="block text-sm text-text-base mb-1">
              Project stage <span className="text-danger">*</span>
            </label>
            <SelectListbox
              value={form.lifecyclePhase}
              onChange={(value: string) =>
                setForm((f) => ({
                  ...f,
                  lifecyclePhase: value as MitigationLifecyclePhase,
                }))
              }
              options={lifecyclePhaseOptions}
              placeholder="Select project stage"
            />
           {/*  <div className="text-xs text-text-faint mt-1">
              Lifecycle area (Construction, Operations & Maintenance, or Users), not the submission stage.
            </div> */}
          </div>

          <div>
            <label className="block text-sm text-text-base mb-1">
              Type <span className="text-danger">*</span>
            </label>
            <SelectListbox
              value={form.type}
              onChange={(value: string) =>
                setForm((f) => ({ ...f, type: value as MitigationType }))
              }
              options={TYPE_OPTIONS}
              placeholder="Select type"
            />
          </div>

          <div>
            <label className="block text-sm text-text-base mb-1">
              Grouping <span className="text-text-faint">(optional)</span>
            </label>
            <input
              className="w-full h-10 bg-white border border-border-input rounded-[var(--radius-3)] px-3 text-sm"
              value={form.group}
              onChange={(e) => setForm((f) => ({ ...f, group: e.target.value }))}
              /* placeholder="e.g. Materials" */
            />
          </div>

          <div>
            <label className="block text-sm text-text-base mb-1">
              Notes <span className="text-text-faint">(optional)</span>
            </label>
            <textarea
              className="w-full bg-white border border-border-input rounded-[var(--radius-3)] px-3 py-2 text-sm h-24"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </div>

          {error && <div className="text-sm text-danger">{error}</div>}
        </div>
      </div>

      <div className="flex justify-end items-center gap-3 px-6 py-4 border-t border-neutral-90 mt-4">
        <button
          type="button"
          onClick={handleClose}
          className="px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] border border-border-input text-text-base hover:bg-neutral-95"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => void handleNext()}
          disabled={busy}
          className="px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] bg-primary text-white hover:bg-primary/90 disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </Modal>
  );
};

const MitigationPhasePlaceholder: React.FC<{
  title: string;
  description: string;
}> = ({ title, description }) => (
  <div className="flex flex-col items-center justify-center px-12 py-20 text-center bg-neutral-98">
    <div className="text-text-dark font-medium max-w-xl">{title}</div>
    <div className="text-sm text-text-faint mt-2 max-w-xl">{description}</div>
  </div>
);

const sumRowsEmissions = (rows: any[]): number =>
  rows.reduce((acc, row) => {
    const v = Number(row.total_emissions_tco2e ?? row.emissions_tco2e ?? 0);
    return acc + (Number.isFinite(v) ? v : 0);
  }, 0);

function rowContributionUsersMitigation(row: any): number {
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

function sumUsersMitigationRowsEmissions(rows: any[]): number {
  return rows.reduce((acc, row) => acc + rowContributionUsersMitigation(row), 0);
}

/**
 * Empty data-entry tables mirroring the main workflow. Rows are local-only.
 * Filtered by lifecycle phase (Construction vs Operations & Maintenance vs Users),
 * then by submission stage (Design vs Construction).
 */
const EmptyMitigationTables: React.FC<{
  submissionStage: StageName;
  lifecyclePhase: MitigationLifecyclePhase;
  projectId: string;
  jurisdictionName?: string | null;
  scopeKey: string;
  collectorRef?: React.MutableRefObject<MitigationTablesCollector | null>;
  hydrateTables?: Record<string, any[]> | null;
  readOnly?: boolean;
  projectMitigationId: string | null;
  saveMitigationNewRow?: MitigationPersistenceApi["saveMitigationNewRow"];
  mitigationMode: MitigationType;
  substitutionLeg: MitigationSubstitutionLeg | null;
  computeEmissionsForRow?: MitigationPersistenceApi["computeEmissionsForRow"];
  onCellChange?: MitigationPersistenceApi["onCellChange"];
  onRowPatch?: MitigationPersistenceApi["onRowPatch"];
  refreshOptionTotals?: MitigationPersistenceApi["refreshOptionTotals"];
  uploadMitigationTableFile?: MitigationPersistenceApi["uploadMitigationTableFile"];
  mitigationStageInstanceId: string | null;
  mitigationProjectOptionId: string | null;
  projectTypeName: string | null;
  opsStartYear: number | null;
}> = ({
  submissionStage,
  lifecyclePhase,
  projectId,
  jurisdictionName,
  scopeKey,
  collectorRef,
  hydrateTables,
  readOnly = false,
  projectMitigationId,
  saveMitigationNewRow,
  mitigationMode,
  substitutionLeg,
  computeEmissionsForRow,
  onCellChange,
  onRowPatch,
  refreshOptionTotals: _refreshOptionTotals,
  uploadMitigationTableFile,
  mitigationStageInstanceId,
  mitigationProjectOptionId,
  projectTypeName,
  opsStartYear,
}) => {
  const useProjectConcrete =
    lifecyclePhase === "construction" && !!computeEmissionsForRow;

  const isMitigationUsersSubStage =
    lifecyclePhase === "users" && submissionStage === "Design";

  const largeUsersHook = useLargeUserYears({
    isUsersSubStage: isMitigationUsersSubStage,
    activeStageInstance: mitigationStageInstanceId
      ? { id: mitigationStageInstanceId }
      : null,
    activeOptionId: mitigationProjectOptionId,
    projectClass: "LARGE",
    isLargeUsersNZ: !!(jurisdictionName ?? "")
      .toLowerCase()
      .includes("new zealand"),
    opsStartYear: opsStartYear ?? null,
    projectId,
    projectMitigationId,
    mitigationSubstitutionLeg: substitutionLeg,
  });

  const [componentRows, setComponentRows] = useState<any[]>([]);
  const [bcDetailedRows, setBcDetailedRows] = useState<any[]>([]);
  const [electricityRows, setElectricityRows] = useState<any[]>([]);
  const [useB1G2Rows, setUseB1G2Rows] = useState<any[]>([]);
  const [useB1G3Rows, setUseB1G3Rows] = useState<any[]>([]);
  const [componentReplRows, setComponentReplRows] = useState<any[]>([]);
  const [refurbRows, setRefurbRows] = useState<any[]>([]);
  const [replDetailedRows, setReplDetailedRows] = useState<any[]>([]);
  const [opEnergyRows, setOpEnergyRows] = useState<any[]>([]);
  const [opEnergyDetailedRows, setOpEnergyDetailedRows] = useState<any[]>([]);
  const [opEnergyElectricityRows, setOpEnergyElectricityRows] = useState<any[]>(
    [],
  );
  const [constructionG2Rows, setConstructionG2Rows] = useState<any[]>([]);
  const [constructionG3Rows, setConstructionG3Rows] = useState<any[]>([]);
  const [concreteRegSimplifiedRows, setConcreteRegSimplifiedRows] = useState<
    any[]
  >([]);

  const [mitigationInlineErr, setMitigationInlineErr] = useState<
    Record<string, string | null>
  >({});

  const wrapMitigationCellChange = useCallback(
    (key: MitigationUploadKey, setRows: React.Dispatch<React.SetStateAction<any[]>>) =>
      onCellChange?.(key, setRows, (msg) =>
        setMitigationInlineErr((e) => ({ ...e, [key]: msg })),
      ),
    [onCellChange],
  );

  const wrapMitigationRowPatch = useCallback(
    (key: MitigationUploadKey, setRows: React.Dispatch<React.SetStateAction<any[]>>) =>
      onRowPatch?.(key, setRows, (msg) =>
        setMitigationInlineErr((e) => ({ ...e, [key]: msg })),
      ),
    [onRowPatch],
  );

  const [accordionState, setAccordionState] = useState<Record<string, boolean>>({
    asset: true,
    component: true,
    bcDetailedLevel: true,
    electricity: true,
    useB1G2: true,
    useB1G3: true,
    componentRepl: true,
    refurbishment: true,
    replDetailed: true,
    opEnergy: true,
    opEnergyDetailed: true,
    opEnergyElectricity: true,
    constructionG2: true,
    constructionG3: true,
    concreteRegSimplified: true,
  });

  const appendMitigationRow = (tk: string, row: any) => {
    switch (tk) {
      case "component":
        setComponentRows((p) => [row, ...p]);
        break;
      case "componentRepl":
        setComponentReplRows((p) => [row, ...p]);
        break;
      case "bcDetailedLevel":
        setBcDetailedRows((p) => [row, ...p]);
        break;
      case "electricity":
        setElectricityRows((p) => [row, ...p]);
        break;
      case "useB1G2":
        setUseB1G2Rows((p) => [row, ...p]);
        break;
      case "useB1G3":
        setUseB1G3Rows((p) => [row, ...p]);
        break;
      case "refurbishment":
        setRefurbRows((p) => [row, ...p]);
        break;
      case "replDetailed":
        setReplDetailedRows((p) => [row, ...p]);
        break;
      case "opEnergy":
        setOpEnergyRows((p) => [row, ...p]);
        break;
      case "opEnergyDetailed":
        setOpEnergyDetailedRows((p) => [row, ...p]);
        break;
      case "opEnergyElectricity":
        setOpEnergyElectricityRows((p) => [row, ...p]);
        break;
      case "constructionG2":
        setConstructionG2Rows((p) => [row, ...p]);
        break;
      case "constructionG3":
        setConstructionG3Rows((p) => [row, ...p]);
        break;
      case "concreteRegSimplified":
        setConcreteRegSimplifiedRows((p) => [row, ...p]);
        break;
      default:
        break;
    }
  };

  const persistLeg =
    mitigationMode === "substitution" ? substitutionLeg : null;

   const [uploadTarget, setUploadTarget] = useState<MitigationUploadKey | null>(
    null,
  );

  const requestMitigationUpload = useCallback(
    (key: MitigationUploadKey) => {
      if (readOnly || !projectMitigationId || !uploadMitigationTableFile) return;
      setUploadTarget(key);
    },
    [readOnly, projectMitigationId, uploadMitigationTableFile],
  );

  const applyMitigationUploadedRows = useCallback(
    (key: MitigationUploadKey, rows: any[]) => {
      switch (key) {
        case "component":
          setComponentRows(rows);
          break;
        case "bcDetailedLevel":
          setBcDetailedRows(rows);
          break;
        case "electricity":
          setElectricityRows(rows);
          break;
        case "useB1G2":
          setUseB1G2Rows(rows);
          break;
        case "useB1G3":
          setUseB1G3Rows(rows);
          break;
        case "componentRepl":
          setComponentReplRows(rows);
          break;
        case "refurbishment":
          setRefurbRows(rows);
          break;
        case "replDetailed":
          setReplDetailedRows(rows);
          break;
        case "opEnergy":
          setOpEnergyRows(rows);
          break;
        case "opEnergyDetailed":
          setOpEnergyDetailedRows(rows);
          break;
        case "opEnergyElectricity":
          setOpEnergyElectricityRows(rows);
          break;
        case "constructionG2":
          setConstructionG2Rows(rows);
          break;
        case "constructionG3":
          setConstructionG3Rows(rows);
          break;
        case "concreteRegSimplified":
          setConcreteRegSimplifiedRows(rows);
          break;
        default:
          break;
      }
    },
    [],
  );

  const wrapMitigationSave =
    (uploadKey: string) => async (draft: any) => {
      if (readOnly || !saveMitigationNewRow || !projectMitigationId) return true;

      const getElecRows = () => {
        if (uploadKey === "electricity" || uploadKey?.endsWith("-electricity")) return electricityRows;
        if (uploadKey === "opEnergyElectricity" || uploadKey?.endsWith("-opEnergyElectricity")) return opEnergyElectricityRows;
        if (isElectricityTable(uploadKey as any)) {
          if (uploadKey.includes("opEnergyElectricity")) return opEnergyElectricityRows;
          return electricityRows;
        }
        return null;
      };
      const getSetElecRows = (): React.Dispatch<React.SetStateAction<any[]>> | null => {
        if (uploadKey === "electricity" || uploadKey?.endsWith("-electricity")) return setElectricityRows;
        if (uploadKey === "opEnergyElectricity" || uploadKey?.endsWith("-opEnergyElectricity")) return setOpEnergyElectricityRows;
        if (isElectricityTable(uploadKey as any)) {
          if (uploadKey.includes("opEnergyElectricity")) return setOpEnergyElectricityRows;
          return setElectricityRows;
        }
        return null;
      };

      const elecRows = isElectricityTable(uploadKey as any) ? getElecRows() : null;
      const existingSiblings = elecRows ? elecRows.filter((r: any) => r._fromApi) : [];

      const ok = await saveMitigationNewRow(
        uploadKey,
        projectMitigationId,
        draft,
        appendMitigationRow,
        (msg) =>
          setMitigationInlineErr((prev) => ({ ...prev, [uploadKey]: msg })),
        persistLeg,
      );

      if (ok && existingSiblings.length > 0 && computeEmissionsForRow) {
        const setElecRows = getSetElecRows();
        if (setElecRows) {
          void (async () => {
            for (const sibling of existingSiblings) {
              try {
                const patch = await computeEmissionsForRow(uploadKey, sibling);
                if (!patch) continue;
                setElecRows((prev: any[]) =>
                  prev.map((r: any) => (r.id === sibling.id ? { ...r, ...patch } : r)),
                );
                const raw = patch.total_emissions_tco2e ?? patch.emissions_tco2e;
                const emissionsNum =
                  raw === "-" || raw == null || Number.isNaN(Number(raw)) ? null : Number(raw);
                const updatedRow = { ...sibling, ...patch };
                const extraFields = {
                  ...updatedRow,
                  location_based_tco2e: patch.location_based_tco2e ?? null,
                  market_based_tco2e: patch.market_based_tco2e ?? null,
                };
                delete extraFields._fromApi;
                await ActivityDataService.updateRow(sibling.id, {
                  quantity: Number(updatedRow.quantity_mwh ?? sibling.quantity ?? 0),
                  emissions_tco2e: emissionsNum,
                  extra_fields: extraFields,
                });
              } catch (e) {
                console.warn("Mitigation: failed to recalc electricity sibling", sibling.id, e);
              }
            }
            try { await _refreshOptionTotals?.(); } catch { /* ignore */ }
          })();
        }
      }

      return ok;
    };
 
const mitigationUploadModal = (
    <UploadModal
      open={uploadTarget != null}
      onClose={() => setUploadTarget(null)}
      parseFile={(file) => {
        if (!uploadTarget) return Promise.resolve([]);
        const config = resolveMitigationUploadConfig(uploadTarget, projectId);
        return parseFileToRows(file, config.fileHeaders, ["quantity"], {});
      }}
      validateRows={async (parsed) => {
        if (!uploadTarget) return { validRows: [], errors: [] };
        const config = resolveMitigationUploadConfig(uploadTarget, projectId);
        const rules = normalizeValidationRules(config.rules || []);
        return validateRows(parsed, rules as any);
      }}
      onSuccess={async (validRows) => {
        if (!uploadTarget || !projectMitigationId || !uploadMitigationTableFile)
          return;
        const key = uploadTarget;
        try {
          const { rows } = await uploadMitigationTableFile(
            key,
            projectMitigationId,
            validRows,
            persistLeg,
          );
          applyMitigationUploadedRows(key, rows);
          setMitigationInlineErr((e) => ({ ...e, [key]: null }));
        } catch (e: any) {
          console.warn("Mitigation bulk upload failed:", e);
          throw new Error(
            e?.message || "Bulk upload failed. Please check uploaded data.",
          );
        }
      }}
    />
  );

  const componentColumns = useMemo(
    () => componentTableConfig(projectId).columns(),
    [projectId]
  );
  const bcDetailedColumns = useMemo(
    () => constructionG3Config(projectId).columns(),
    [projectId]
  );
  const electricityColumns = useMemo(() => electricityConfig(projectId).columns(), [projectId]);
  const useB1G2Columns = useMemo(
    () => useB1G2Config(null, projectId).columns(),
    [projectId]
  );
  const useB1G3Columns = useMemo(() => useB1G3Config(projectId).columns(), [projectId]);
  const componentReplColumns = useMemo(
    () => componentReplacementConfig(projectId).columns(),
    [projectId]
  );
  const refurbColumns = useMemo(() => refurbishmentTableConfig(jurisdictionName).columns(), [jurisdictionName]);
  const opEnergyColumns = useMemo(() => opEnergyTableConfig(projectId).columns(), [projectId]);
  const replDetailedColumns = useMemo(
    () => useB1G3Config(projectId).columns(),
    [projectId]
  );
  const opEnergyDetailedColumns = useMemo(
    () => useB1G3Config(projectId, ["Fuels", "Water"]).columns(),
    [projectId]
  );
  const opEnergyElectricityColumns = useMemo(
    () => electricityConfig(projectId).columns(),
    [projectId]
  );
  const constructionG2Columns = useMemo(
    () => constructionG2Config(projectId).columns(),
    [projectId]
  );
  const constructionG3Columns = useMemo(
    () => constructionG3Config(projectId).columns(),
    [projectId]
  );
  const concreteSimplifiedColumns = useMemo(
    () => concreteRegSimplifiedConfig().columns(),
    [],
  );

  useEffect(() => {
    setMitigationInlineErr({});
  }, [projectMitigationId, hydrateTables]);

  useEffect(() => {
    if (!hydrateTables) return;
    const h = hydrateTables;
    if (h.component) setComponentRows(h.component);
    if (h.bcDetailedLevel) setBcDetailedRows(h.bcDetailedLevel);
    if (h.electricity) setElectricityRows(h.electricity);
    if (h.useB1G2) setUseB1G2Rows(h.useB1G2);
    if (h.useB1G3) setUseB1G3Rows(h.useB1G3);
    if (h.componentRepl) setComponentReplRows(h.componentRepl);
    if (h.refurbishment) setRefurbRows(h.refurbishment);
    if (h.replDetailed) setReplDetailedRows(h.replDetailed);
    if (h.opEnergy) setOpEnergyRows(h.opEnergy);
    if (h.opEnergyDetailed) setOpEnergyDetailedRows(h.opEnergyDetailed);
    if (h.opEnergyElectricity)
      setOpEnergyElectricityRows(h.opEnergyElectricity);
    if (h.constructionG2) setConstructionG2Rows(h.constructionG2);
    if (h.constructionG3) setConstructionG3Rows(h.constructionG3);
    if (h.concreteRegSimplified !== undefined) {
      setConcreteRegSimplifiedRows(h.concreteRegSimplified);
    }
  }, [hydrateTables]);

  useLayoutEffect(() => {
    if (!collectorRef) return;
    const collect = (): Record<string, any[]> => {
      const keys = getMitigationPanelBaseKeys(submissionStage, lifecyclePhase);
      const map: Record<string, any[]> = {};
      for (const k of keys) {
        switch (k) {
          case "component":
            map.component = componentRows;
            break;
          case "bcDetailedLevel":
            map.bcDetailedLevel = bcDetailedRows;
            break;
          case "electricity":
            map.electricity = electricityRows;
            break;
          case "useB1G2":
            map.useB1G2 = useB1G2Rows;
            break;
          case "useB1G3":
            map.useB1G3 = useB1G3Rows;
            break;
          case "componentRepl":
            map.componentRepl = componentReplRows;
            break;
          case "refurbishment":
            map.refurbishment = refurbRows;
            break;
          case "replDetailed":
            map.replDetailed = replDetailedRows;
            break;
          case "opEnergy":
            map.opEnergy = opEnergyRows;
            break;
          case "opEnergyDetailed":
            map.opEnergyDetailed = opEnergyDetailedRows;
            break;
          case "opEnergyElectricity":
            map.opEnergyElectricity = opEnergyElectricityRows;
            break;
          case "constructionG2":
            map.constructionG2 = constructionG2Rows;
            break;
          case "constructionG3":
            map.constructionG3 = constructionG3Rows;
            break;
          case "concreteRegSimplified":
            map.concreteRegSimplified = concreteRegSimplifiedRows;
            break;
          default:
            break;
        }
      }
      return map;
    };
    collectorRef.current = { collect };
  }, [
    collectorRef,
    submissionStage,
    lifecyclePhase,
    componentRows,
    bcDetailedRows,
    electricityRows,
    useB1G2Rows,
    useB1G3Rows,
    componentReplRows,
    refurbRows,
    replDetailedRows,
    opEnergyRows,
    opEnergyDetailedRows,
    opEnergyElectricityRows,
    constructionG2Rows,
    constructionG3Rows,
    concreteRegSimplifiedRows,
  ]);

  const renderEditor = (col: any, props: any) =>
    MitigationCellEditor(col, props);

  const scopeDiv = <div className="hidden">{scopeKey}</div>;

  if (lifecyclePhase === "users") {
    if (submissionStage !== "Design") {
      return (
        <>
          <MitigationPhasePlaceholder
            title="Users not available"
            description="Users lifecycle data entry applies only when the project submission stage is Design."
          />
          {scopeDiv}
        </>
      );
    }
    if (!mitigationStageInstanceId) {
      return (
        <>
          <MitigationPhasePlaceholder
            title="Users — setup in progress"
            description="Could not resolve the mitigation stage. Try closing and reopening the wizard."
          />
          {scopeDiv}
        </>
      );
    }
    return (
      <>
        <UsersSubStage
          stageInstanceId={mitigationStageInstanceId}
          projectId={projectId}
          optionId={mitigationProjectOptionId ?? null}
          refreshKey={largeUsersHook.usersRefreshKey}
          readOnly={readOnly}
          jurisdiction={jurisdictionName ?? null}
          projectClass="LARGE"
          projectTypeName={projectTypeName}
          opsStartYear={opsStartYear ?? null}
          activeLargeUsersYear={largeUsersHook.activeLargeUsersYear}
          largeUsersYears={largeUsersHook.largeUsersYears}
          onActiveLargeUsersYearChange={largeUsersHook.setActiveLargeUsersYear}
          onOpenAddLargeYear={() => largeUsersHook.setAddLargeYearOpen(true)}
          onOpenCopyLargeYear={() =>
            largeUsersHook.setCopyLargeYearConfirmOpen(true)
          }
          onOpenDeleteLargeYear={() =>
            largeUsersHook.setDeleteLargeYearConfirmOpen(true)
          }
          projectMitigationId={projectMitigationId}
          mitigationSubstitutionLeg={substitutionLeg}
        />
        {largeUsersHook.addLargeYearOpen && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-full">
              <h3 className="text-lg font-semibold mb-4">Add modelled year</h3>
              <input
                type="number"
                className="h-9 w-full border border-border-input rounded px-2 text-sm mb-2"
                placeholder="e.g. 2050"
                value={largeUsersHook.addLargeYearInput}
                onChange={(e) => {
                  largeUsersHook.setAddLargeYearInput(e.target.value);
                  largeUsersHook.setAddLargeYearError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void largeUsersHook.handleAddLargeYear();
                  if (e.key === "Escape") {
                    largeUsersHook.setAddLargeYearOpen(false);
                    largeUsersHook.setAddLargeYearInput("");
                    largeUsersHook.setAddLargeYearError(null);
                  }
                }}
                autoFocus
              />
              {largeUsersHook.addLargeYearError && (
                <p className="text-xs text-danger mb-2">
                  {largeUsersHook.addLargeYearError}
                </p>
              )}
              <div className="flex justify-end gap-3 mt-4">
                <button
                  type="button"
                  onClick={() => {
                    largeUsersHook.setAddLargeYearOpen(false);
                    largeUsersHook.setAddLargeYearInput("");
                    largeUsersHook.setAddLargeYearError(null);
                  }}
                  className="px-4 py-2 text-sm cursor-pointer border border-neutral-300 rounded hover:bg-neutral-100"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => void largeUsersHook.handleAddLargeYear()}
                  className="px-4 py-2 text-sm cursor-pointer bg-primary text-white rounded hover:bg-primary/90"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        )}
        {largeUsersHook.copyLargeYearConfirmOpen && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-full">
              <h3 className="text-lg font-semibold mb-2">Copy from another year</h3>
              <p className="text-sm text-text-base mb-4">
                Select a source year to copy data into year{" "}
                <strong>{largeUsersHook.activeLargeUsersYear}</strong>. This will
                overwrite all existing data for that year.
              </p>
              <select
                className="h-9 w-full border border-border-input rounded px-2 text-sm bg-white mb-4"
                value={largeUsersHook.copyLargeYearSource ?? ""}
                onChange={(e) =>
                  largeUsersHook.setCopyLargeYearSource(
                    e.target.value ? Number(e.target.value) : null,
                  )
                }
              >
                <option value="">Select year…</option>
                {largeUsersHook.largeUsersYears
                  .filter((y) => y !== largeUsersHook.activeLargeUsersYear)
                  .map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
              </select>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    largeUsersHook.setCopyLargeYearConfirmOpen(false);
                    largeUsersHook.setCopyLargeYearSource(null);
                  }}
                  className="px-4 py-2 text-sm cursor-pointer border border-neutral-300 rounded hover:bg-neutral-100"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={largeUsersHook.copyLargeYearSource === null}
                  onClick={() => void largeUsersHook.handleCopyLargeYear()}
                  className="px-4 py-2 text-sm cursor-pointer bg-primary text-white rounded hover:bg-primary/90 disabled:opacity-50"
                >
                  Copy
                </button>
              </div>
            </div>
          </div>
        )}
        {largeUsersHook.deleteLargeYearConfirmOpen &&
          largeUsersHook.activeLargeUsersYear !== null && (
            <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40">
              <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-full">
                <h3 className="text-lg font-semibold mb-2">
                  Delete modelled year {largeUsersHook.activeLargeUsersYear}?
                </h3>
                <p className="text-sm text-text-base mb-6">
                  All road user, rail user, and road parameter data for year{" "}
                  <strong>{largeUsersHook.activeLargeUsersYear}</strong> will be
                  removed for this mitigation. This cannot be undone.
                </p>
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() =>
                      largeUsersHook.setDeleteLargeYearConfirmOpen(false)
                    }
                    className="px-4 py-2 text-sm cursor-pointer border border-neutral-300 rounded hover:bg-neutral-100"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => void largeUsersHook.handleDeleteLargeYear()}
                    className="px-4 py-2 cursor-pointer text-sm bg-danger text-white rounded hover:bg-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          )}
        {scopeDiv}
      </>
    );
  }

  const opEnergySectionTitle =
    submissionStage === "Construction"
      ? "Operational energy (B6) and Water (B7)"
      : "Operational energy (B6)";

  if (lifecyclePhase === "operations_maintenance") {
    return (
      <div className="flex flex-col">
        <div className="px-12 pt-6 pb-2 text-text-base text-sm font-medium uppercase tracking-wide">
          Use (B1)
        </div>
        <TableWrapper readOnly={readOnly}
          title="Component Level (Grade 2)"
          rows={useB1G2Rows}
          setRows={setUseB1G2Rows}
          columns={useB1G2Columns}
          exportFileName="Mitigation_UseB1_ComponentLevel.csv"
          uploadKey="useB1G2"
          renderEditor={renderEditor}
         onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.useB1G2 ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, useB1G2: null }))
          }
          onNewRowSave={wrapMitigationSave("useB1G2")}
          onCellChange={wrapMitigationCellChange("useB1G2", setUseB1G2Rows)}
          onRowPatch={wrapMitigationRowPatch("useB1G2", setUseB1G2Rows)}
          accordionKey="useB1G2"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setUseB1G2Rows((prev) => prev.filter((r) => r.id !== id))
          }
        />
        <TableWrapper readOnly={readOnly}
          title="Detailed Level (Grade 3)"
          rows={useB1G3Rows}
          setRows={setUseB1G3Rows}
          columns={useB1G3Columns}
          exportFileName="Mitigation_UseB1_DetailedLevel.csv"
          uploadKey="useB1G3"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.useB1G3 ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, useB1G3: null }))
          }
          onNewRowSave={wrapMitigationSave("useB1G3")}
          onCellChange={wrapMitigationCellChange("useB1G3", setUseB1G3Rows)}
          onRowPatch={wrapMitigationRowPatch("useB1G3", setUseB1G3Rows)}
          accordionKey="useB1G3"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setUseB1G3Rows((prev) => prev.filter((r) => r.id !== id))
          }
        />

        <div className="px-12 pt-6 pb-2 text-text-base text-sm font-medium uppercase tracking-wide">
          Maintenance, Repair, Replacement and Refurbishment (B2-B5)
        </div>
        <TableWrapper readOnly={readOnly}
          title="Component level replacement"
          rows={componentReplRows}
          setRows={setComponentReplRows}
          columns={componentReplColumns}
          exportFileName="Mitigation_ComponentLevelReplacement.csv"
          uploadKey="componentRepl"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.componentRepl ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, componentRepl: null }))
          }
          onNewRowSave={wrapMitigationSave("componentRepl")}
          onCellChange={wrapMitigationCellChange("componentRepl", setComponentReplRows)}
          onRowPatch={wrapMitigationRowPatch("componentRepl", setComponentReplRows)}
          accordionKey="componentRepl"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setComponentReplRows((prev) => prev.filter((r) => r.id !== id))
          }
        />
        <TableWrapper readOnly={readOnly}
          title="Other partial replacement or refurbishment activities"
          rows={refurbRows}
          setRows={setRefurbRows}
          columns={refurbColumns}
          exportFileName="Mitigation_Replacement_Refurbishment.csv"
          uploadKey="refurbishment"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.refurbishment ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, refurbishment: null }))
          }
          onNewRowSave={wrapMitigationSave("refurbishment")}
          onCellChange={wrapMitigationCellChange("refurbishment", setRefurbRows)}
          onRowPatch={wrapMitigationRowPatch("refurbishment", setRefurbRows)}
          accordionKey="refurbishment"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setRefurbRows((prev) => prev.filter((r) => r.id !== id))
          }
        />
        <TableWrapper readOnly={readOnly}
          title="Detailed Level (Grade 3)"
          rows={replDetailedRows}
          setRows={setReplDetailedRows}
          columns={replDetailedColumns}
          exportFileName="Mitigation_Replacement_DetailedLevel.csv"
          uploadKey="replDetailed"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.replDetailed ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, replDetailed: null }))
          }
          onNewRowSave={wrapMitigationSave("replDetailed")}
          onCellChange={wrapMitigationCellChange("replDetailed", setReplDetailedRows)}
          onRowPatch={wrapMitigationRowPatch("replDetailed", setReplDetailedRows)}
          accordionKey="replDetailed"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setReplDetailedRows((prev) => prev.filter((r) => r.id !== id))
          }
        />

        <div className="px-12 pt-6 pb-2 text-text-base text-sm font-medium uppercase tracking-wide">
          {opEnergySectionTitle}
        </div>
        <TableWrapper readOnly={readOnly}
          title="Component level (grade 2)"
          rows={opEnergyRows}
          setRows={setOpEnergyRows}
          columns={opEnergyColumns}
          exportFileName="Mitigation_OperationalEnergy.csv"
          uploadKey="opEnergy"
          renderEditor={renderEditor}
           onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.opEnergy ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, opEnergy: null }))
          }
          onNewRowSave={wrapMitigationSave("opEnergy")}
          onCellChange={wrapMitigationCellChange("opEnergy", setOpEnergyRows)}
          onRowPatch={wrapMitigationRowPatch("opEnergy", setOpEnergyRows)}
          accordionKey="opEnergy"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setOpEnergyRows((prev) => prev.filter((r) => r.id !== id))
          }
        />
        <TableWrapper readOnly={readOnly}
          title="Detailed Level (Grade 3)"
          rows={opEnergyDetailedRows}
          setRows={setOpEnergyDetailedRows}
          columns={opEnergyDetailedColumns}
          exportFileName="Mitigation_OperationalEnergy_DetailedLevel.csv"
          uploadKey="opEnergyDetailed"
          renderEditor={renderEditor}
           onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.opEnergyDetailed ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, opEnergyDetailed: null }))
          }
          onNewRowSave={wrapMitigationSave("opEnergyDetailed")}
          onCellChange={wrapMitigationCellChange("opEnergyDetailed", setOpEnergyDetailedRows)}
          onRowPatch={wrapMitigationRowPatch("opEnergyDetailed", setOpEnergyDetailedRows)}
          accordionKey="opEnergyDetailed"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setOpEnergyDetailedRows((prev) => prev.filter((r) => r.id !== id))
          }
        />
        <TableWrapper readOnly={readOnly}
          title="Electricity"
          rows={opEnergyElectricityRows}
          setRows={setOpEnergyElectricityRows}
          columns={opEnergyElectricityColumns}
          exportFileName="Mitigation_OperationalEnergy_Electricity.csv"
          uploadKey="opEnergyElectricity"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.opEnergyElectricity ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({
              ...e,
              opEnergyElectricity: null,
            }))
          }
          onNewRowSave={wrapMitigationSave("opEnergyElectricity")}
          onCellChange={wrapMitigationCellChange("opEnergyElectricity", setOpEnergyElectricityRows)}
          onRowPatch={wrapMitigationRowPatch("opEnergyElectricity", setOpEnergyElectricityRows)}
          accordionKey="opEnergyElectricity"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setOpEnergyElectricityRows((prev) =>
              prev.filter((r) => r.id !== id)
            )
          }
        />
        {mitigationUploadModal}
        {scopeDiv}
      </div>
    );
  }

  // lifecyclePhase === "construction"
  if (submissionStage === "Design") {
    return (
      <div className="flex flex-col">
        <div className="px-12 py-4 text-text-base text-sm font-medium uppercase tracking-wide">
          Construction
        </div>
        <TableWrapper readOnly={readOnly}
          title="Component level"
          rows={componentRows}
          setRows={setComponentRows}
          columns={componentColumns}
          exportFileName="Mitigation_ComponentLevel.csv"
          uploadKey="component"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.component ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, component: null }))
          }
          onNewRowSave={wrapMitigationSave("component")}
          onCellChange={wrapMitigationCellChange("component", setComponentRows)}
          onRowPatch={wrapMitigationRowPatch("component", setComponentRows)}
          accordionKey="component"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setComponentRows((prev) => prev.filter((r) => r.id !== id))
          }
        />
        <TableWrapper readOnly={readOnly}
          title="Detailed level (Grade 3 & 4)"
          rows={bcDetailedRows}
          setRows={setBcDetailedRows}
          columns={bcDetailedColumns}
          exportFileName="Mitigation_DetailedLevel.csv"
          uploadKey="bcDetailedLevel"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.bcDetailedLevel ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, bcDetailedLevel: null }))
          }
          onNewRowSave={wrapMitigationSave("bcDetailedLevel")}
          onCellChange={wrapMitigationCellChange("bcDetailedLevel", setBcDetailedRows)}
          onRowPatch={wrapMitigationRowPatch("bcDetailedLevel", setBcDetailedRows)}
          accordionKey="bcDetailedLevel"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setBcDetailedRows((prev) => prev.filter((r) => r.id !== id))
          }
        />
        <TableWrapper readOnly={readOnly}
          title="Electricity"
          rows={electricityRows}
          setRows={setElectricityRows}
          columns={electricityColumns}
          exportFileName="Mitigation_Electricity.csv"
          uploadKey="electricity"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          error={mitigationInlineErr.electricity ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({ ...e, electricity: null }))
          }
          onNewRowSave={wrapMitigationSave("electricity")}
          onCellChange={wrapMitigationCellChange("electricity", setElectricityRows)}
          onRowPatch={wrapMitigationRowPatch("electricity", setElectricityRows)}
          accordionKey="electricity"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          onDeleteRow={(id) =>
            setElectricityRows((prev) => prev.filter((r) => r.id !== id))
          }
        />
        {useProjectConcrete && (
          <TableWrapper
            readOnly={readOnly}
            title="Concrete register (grade 3) - simplified"
            rows={concreteRegSimplifiedRows}
            setRows={setConcreteRegSimplifiedRows}
            columns={concreteSimplifiedColumns}
            exportFileName="Concrete_Register_simplified.csv"
            uploadKey="concreteRegSimplified"
            renderEditor={renderEditor}
            onRequestUpload={requestMitigationUpload}
            onNewRowSave={wrapMitigationSave("concreteRegSimplified")}
            onCellChange={wrapMitigationCellChange("concreteRegSimplified", setConcreteRegSimplifiedRows)}
            onRowPatch={wrapMitigationRowPatch("concreteRegSimplified", setConcreteRegSimplifiedRows)}
            accordionKey="concreteRegSimplified"
            accordionState={accordionState as any}
            setAccordionState={setAccordionState as any}
            error={mitigationInlineErr.concreteRegSimplified ?? null}
            onCancel={() =>
              setMitigationInlineErr((e) => ({
                ...e,
                concreteRegSimplified: null,
              }))
            }
            onDeleteRow={
              !readOnly
                ? (id) =>
                    setConcreteRegSimplifiedRows((prev) =>
                      prev.filter((r) => r.id !== id),
                    )
                : undefined
            }
          />
        )}
        {mitigationUploadModal}
        {scopeDiv}
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <div className="px-12 py-4 text-text-base text-sm font-medium uppercase tracking-wide">
        Construction
      </div>
      <TableWrapper readOnly={readOnly}
        title="Component level"
        rows={constructionG2Rows}
        setRows={setConstructionG2Rows}
        columns={constructionG2Columns}
        exportFileName="Mitigation_ConstructionG2.csv"
        uploadKey="constructionG2"
        renderEditor={renderEditor}
        onRequestUpload={requestMitigationUpload}
        error={mitigationInlineErr.constructionG2 ?? null}
        onCancel={() =>
          setMitigationInlineErr((e) => ({ ...e, constructionG2: null }))
        }
        onNewRowSave={wrapMitigationSave("constructionG2")}
        onCellChange={wrapMitigationCellChange("constructionG2", setConstructionG2Rows)}
        onRowPatch={wrapMitigationRowPatch("constructionG2", setConstructionG2Rows)}
        accordionKey="constructionG2"
        accordionState={accordionState as any}
        setAccordionState={setAccordionState as any}
        onDeleteRow={(id) =>
          setConstructionG2Rows((prev) => prev.filter((r) => r.id !== id))
        }
      />
      <TableWrapper readOnly={readOnly}
        title="Detailed level - construction stage"
        rows={constructionG3Rows}
        setRows={setConstructionG3Rows}
        columns={constructionG3Columns}
        exportFileName="Mitigation_ConstructionG3.csv"
        uploadKey="constructionG3"
        renderEditor={renderEditor}
        onRequestUpload={requestMitigationUpload}
        error={mitigationInlineErr.constructionG3 ?? null}
        onCancel={() =>
          setMitigationInlineErr((e) => ({ ...e, constructionG3: null }))
        }
        onNewRowSave={wrapMitigationSave("constructionG3")}
        onCellChange={wrapMitigationCellChange("constructionG3", setConstructionG3Rows)}
        onRowPatch={wrapMitigationRowPatch("constructionG3", setConstructionG3Rows)}
        accordionKey="constructionG3"
        accordionState={accordionState as any}
        setAccordionState={setAccordionState as any}
        onDeleteRow={(id) =>
          setConstructionG3Rows((prev) => prev.filter((r) => r.id !== id))
        }
      />
      <TableWrapper readOnly={readOnly}
        title="Electricity"
        rows={electricityRows}
        setRows={setElectricityRows}
        columns={electricityColumns}
        exportFileName="Mitigation_Construction_Electricity.csv"
        uploadKey="electricity"
        renderEditor={renderEditor}
        onRequestUpload={requestMitigationUpload}
        error={mitigationInlineErr.electricity ?? null}
        onCancel={() =>
          setMitigationInlineErr((e) => ({ ...e, electricity: null }))
        }
        onNewRowSave={wrapMitigationSave("electricity")}
        onCellChange={wrapMitigationCellChange("electricity", setElectricityRows)}
        onRowPatch={wrapMitigationRowPatch("electricity", setElectricityRows)}
        accordionKey="electricity"
        accordionState={accordionState as any}
        setAccordionState={setAccordionState as any}
        onDeleteRow={(id) =>
          setElectricityRows((prev) => prev.filter((r) => r.id !== id))
        }
      />
      {useProjectConcrete && (
        <TableWrapper
          readOnly={readOnly}
          title="Concrete register (grade 3) - simplified"
          rows={concreteRegSimplifiedRows}
          setRows={setConcreteRegSimplifiedRows}
          columns={concreteSimplifiedColumns}
          exportFileName="Concrete_Register_simplified.csv"
          uploadKey="concreteRegSimplified"
          renderEditor={renderEditor}
          onRequestUpload={requestMitigationUpload}
          onNewRowSave={wrapMitigationSave("concreteRegSimplified")}
          onCellChange={wrapMitigationCellChange("concreteRegSimplified", setConcreteRegSimplifiedRows)}
          onRowPatch={wrapMitigationRowPatch("concreteRegSimplified", setConcreteRegSimplifiedRows)}
          accordionKey="concreteRegSimplified"
          accordionState={accordionState as any}
          setAccordionState={setAccordionState as any}
          error={mitigationInlineErr.concreteRegSimplified ?? null}
          onCancel={() =>
            setMitigationInlineErr((e) => ({
              ...e,
              concreteRegSimplified: null,
            }))
          }
          onDeleteRow={
            !readOnly
              ? (id) =>
                  setConcreteRegSimplifiedRows((prev) =>
                    prev.filter((r) => r.id !== id),
                  )
              : undefined
          }
        />
      )}
      {mitigationUploadModal}
      {scopeDiv}
    </div>
  );
};

const Step2Modal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  draft: Step1Form | null;
  submissionStage: StageName;
  projectId: string;
  jurisdictionName?: string | null;
  mitigationScenarioId: string | null;
  persistence: MitigationPersistenceApi | null;
  hydrateSnapshot: MitigationHydrate | null;
  detailReadOnly: boolean;
  tablesCollectorRef: React.MutableRefObject<{
    collect: () => MitigationWizardSnapshot;
  } | null>;
  onPersisted: () => void | Promise<void>;
  mitigationStageInstanceId: string | null;
  mitigationProjectOptionId: string | null;
  projectTypeName: string | null;
  opsStartYear: number | null;
}> = ({
  isOpen,
  onClose,
  draft,
  submissionStage,
  projectId,
  jurisdictionName,
  mitigationScenarioId,
  persistence,
  hydrateSnapshot,
  detailReadOnly,
  tablesCollectorRef,
  onPersisted,
  mitigationStageInstanceId,
  mitigationProjectOptionId,
  projectTypeName,
  opsStartYear,
}) => {
  const isSubstitution = draft?.type === "substitution";
  const innerCollectorRef = useRef<MitigationTablesCollector | null>(null);
  const replacedCollectorRef = useRef<MitigationTablesCollector | null>(
    null,
  );
  const adoptedCollectorRef = useRef<MitigationTablesCollector | null>(null);

  const [subStep, setSubStep] = useState<1 | 2>(1);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) setSubStep(1);
  }, [isOpen]);

  useLayoutEffect(() => {
    tablesCollectorRef.current = {
      collect: () => {
        if (draft?.type === "substitution") {
          return {
            mode: "substitution",
            replaced: replacedCollectorRef.current?.collect() ?? {},
            adopted: adoptedCollectorRef.current?.collect() ?? {},
          };
        }
        return {
          mode: "reduction",
          tables: innerCollectorRef.current?.collect() ?? {},
        };
      },
    };
  }, [draft?.type, draft?.lifecyclePhase, submissionStage, tablesCollectorRef]);

  const handleSaveMitigation = async () => {
    if (
      detailReadOnly ||
      !draft?.lifecyclePhase ||
      !mitigationScenarioId ||
      !persistence
    ) {
      return;
    }
    setSaving(true);
    try {
      const snap = tablesCollectorRef.current?.collect();
      if (!snap) {
        return;
      }
      const keys = getMitigationPanelBaseKeys(
        submissionStage,
        draft.lifecyclePhase as MitigationLifecyclePhase,
      );
      if (snap.mode === "reduction") {
        for (const k of keys) {
          await persistence.saveMitigationBulkTable(
            k,
            mitigationScenarioId,
            snap.tables[k] ?? [],
          );
        }
      } else {
        for (const k of keys) {
          await persistence.saveMitigationBulkTable(
            k,
            mitigationScenarioId,
            snap.replaced[k] ?? [],
            "replaced",
          );
          await persistence.saveMitigationBulkTable(
            k,
            mitigationScenarioId,
            snap.adopted[k] ?? [],
            "adopted",
          );
        }
      }
      await persistence.patchMitigationMeta(mitigationScenarioId, {
        name: draft.name.trim(),
        type: draft.type || "reduction",
        lifecyclePhase: draft.lifecyclePhase,
        lifecyclePhaseLabel:
          LIFECYCLE_PHASE_LABEL[draft.lifecyclePhase as MitigationLifecyclePhase],
        notes: draft.notes?.trim(),
        group: draft.group?.trim(),
        submissionStage,
      });
      await onPersisted();
      onClose();
    } catch (e) {
      console.warn("Mitigation save failed:", e);
    } finally {
      setSaving(false);
    }
  };

  if (!draft) return null;

  const subTitle = isSubstitution
    ? subStep === 1
      ? "Source(s) replaced"
      : "Source(s) adopted"
    : "";

  const reductionHydrate =
    hydrateSnapshot?.kind === "reduction" ? hydrateSnapshot.tables : null;
  const substReplacedHydrate =
    hydrateSnapshot?.kind === "substitution"
      ? hydrateSnapshot.replaced
      : null;
  const substAdoptedHydrate =
    hydrateSnapshot?.kind === "substitution" ? hydrateSnapshot.adopted : null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="New mitigation"
      className="max-w-[1280px] mx-4 my-6"
    >
      <div className="flex flex-col h-[90vh]">
        <div className="flex items-center justify-between px-8 py-4 border-b border-neutral-90">
          <div>
            <div className="text-2xl text-text-dark">{draft.name}</div>
            <div className="text-sm text-text-faint mt-0.5">
              {TYPE_LABEL[draft.type as MitigationType]}
              {draft.group ? ` • ${draft.group}` : ""}
              {subTitle ? ` • ${subTitle}` : ""}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-base  cursor-pointer hover:bg-neutral-95 p-1 rounded transition-colors"
            aria-label="Close"
          >
            <span className="material-symbols-rounded">close</span>
          </button>
        </div>

        {isSubstitution && (
          <div className="px-8 pt-5 pb-2">
            <SteppedProgressBar
              steps={["Source(s) replaced", "Source(s) adopted"]}
              currentStep={subStep}
            />
          </div>
        )}

        <div
          key={mitigationScenarioId ?? "new-scenario"}
          className="flex-1 overflow-y-auto bg-neutral-98"
        >
          {isSubstitution ? (
            <>
              <div className={subStep === 1 ? "block" : "hidden"}>
                <EmptyMitigationTables
                  submissionStage={submissionStage}
                  lifecyclePhase={draft.lifecyclePhase as MitigationLifecyclePhase}
                  projectId={projectId}
                  jurisdictionName={jurisdictionName}
                  scopeKey={`${mitigationScenarioId ?? "new"}-${draft.lifecyclePhase}-replaced`}
                  collectorRef={replacedCollectorRef}
                  hydrateTables={substReplacedHydrate}
                  readOnly={detailReadOnly}
                  projectMitigationId={mitigationScenarioId}
                  saveMitigationNewRow={persistence?.saveMitigationNewRow}
                  mitigationMode="substitution"
                  substitutionLeg="replaced"
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
              </div>
              <div className={subStep === 2 ? "block" : "hidden"}>
                <EmptyMitigationTables
                  submissionStage={submissionStage}
                  lifecyclePhase={draft.lifecyclePhase as MitigationLifecyclePhase}
                  projectId={projectId}
                  jurisdictionName={jurisdictionName}
                  scopeKey={`${mitigationScenarioId ?? "new"}-${draft.lifecyclePhase}-adopted`}
                  collectorRef={adoptedCollectorRef}
                  hydrateTables={substAdoptedHydrate}
                  readOnly={detailReadOnly}
                  projectMitigationId={mitigationScenarioId}
                  saveMitigationNewRow={persistence?.saveMitigationNewRow}
                  mitigationMode="substitution"
                  substitutionLeg="adopted"
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
              </div>
            </>
          ) : (
            <EmptyMitigationTables
              submissionStage={submissionStage}
              lifecyclePhase={draft.lifecyclePhase as MitigationLifecyclePhase}
              projectId={projectId}
              jurisdictionName={jurisdictionName}
              scopeKey={`${mitigationScenarioId ?? "new"}-${draft.lifecyclePhase}`}
              collectorRef={innerCollectorRef}
              hydrateTables={reductionHydrate}
              readOnly={detailReadOnly}
              projectMitigationId={mitigationScenarioId}
              saveMitigationNewRow={persistence?.saveMitigationNewRow}
              mitigationMode="reduction"
              substitutionLeg={null}
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
          )}
        </div>

        <div className="flex justify-between items-center gap-3 px-8 py-4 border-t border-neutral-90 bg-white">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] border border-border-input text-text-base hover:bg-neutral-95"
          >
            {detailReadOnly ? "Close" : "Cancel"}
          </button>
          {!detailReadOnly && (
            <div className="flex items-center gap-3">
              {isSubstitution && subStep === 2 && (
                <button
                  type="button"
                  onClick={() => setSubStep(1)}
                  className="px-4 py-2 text-sm  cursor-pointer rounded-[var(--radius-3)] border border-border-input text-text-base hover:bg-neutral-95"
                >
                  Back
                </button>
              )}
              {isSubstitution && subStep === 1 ? (
                <button
                  type="button"
                  onClick={() => setSubStep(2)}
                  className="px-4 py-2 text-sm cursor-pointer rounded-[var(--radius-3)] bg-primary text-white hover:bg-primary/90"
                >
                  Next
                </button>
              ) : (
                <button
                  type="button"
                  disabled={saving || !persistence || !mitigationScenarioId}
                  onClick={() => void handleSaveMitigation()}
                  className="px-4 py-2 text-sm rounded-[var(--radius-3)] bg-primary cursor-pointer text-white hover:bg-primary/90 disabled:opacity-40"
                >
                  Save mitigation
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};

const MitigationSummaryView: React.FC<{
  mitigations: Mitigation[];

  embedded?: boolean;
}> = ({ mitigations, embedded = false }) => {
  const maxSaving =
    mitigations.length > 0
      ? Math.max(...mitigations.map((m) => m.estimatedSavingTco2e || 0), 1)
      : 1;

  return (
 <div
      className={
        embedded
          ? "flex flex-col flex-1 min-h-0 w-full"
          : "px-12 py-6 flex flex-col flex-1 min-h-0"
      }
    >
      {!embedded && (
        <h2 className="text-2xl text-text-dark mb-6">Mitigations summary</h2>
      )}
      <div className="bg-white border border-neutral-90 rounded-[var(--radius-3)] p-6 flex-1 min-h-0 flex flex-col">
        <div className="flex text-sm font-medium text-text-base border-b border-neutral-90 pb-3 mb-4 shrink-0">
          <div className="flex-1">Mitigation name</div>
          <div className="w-52 text-right shrink-0">
            Total savings (tCO<sub>2</sub>e)
          </div>
        </div>
        <div className="flex flex-col gap-4 overflow-y-auto flex-1 min-h-0 pr-1">
          {mitigations.length === 0 ? (
            <div className="text-sm text-text-faint py-8 text-center">
              No mitigations to summarize yet.
            </div>
          ) : (
            mitigations.map((m) => {
              const v = m.estimatedSavingTco2e || 0;
              const pct =
                maxSaving > 0 ? Math.min(100, (v / maxSaving) * 100) : 0;
              return (
                <div key={m.id} className="flex items-center gap-4">
                  <div className="flex-1 text-sm text-text-dark truncate">
                    {m.name}
                  </div>
                  <div className="w-52 flex items-center gap-2 justify-end shrink-0">
                    <div className="flex-1 min-w-[72px] h-2 bg-neutral-95 rounded overflow-hidden">
                      <div
                        className="h-full bg-success/70 rounded"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="tabular-nums text-sm text-text-dark w-[110px] text-right">
                      {v.toLocaleString(undefined, {
                        minimumFractionDigits: 1,
                        maximumFractionDigits: 1,
                      })}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

const MitigationsList: React.FC<{
  mitigations: Mitigation[];
  onAdd?: () => void;
  onDelete?: (id: string) => void;
  onEdit?: (m: Mitigation) => void;
  allowMutations?: boolean;
  viewOnlyInteraction?: boolean;
  onOpenRow?: (m: Mitigation) => void;
 
  embedded?: boolean;
}> = ({
  mitigations,
  onAdd,
  onDelete,
  onEdit,
  allowMutations = true,
  viewOnlyInteraction = false,
  onOpenRow,
  embedded = false,
}) => {
  const totalSaving = mitigations.reduce(
    (sum, m) => sum + (m.estimatedSavingTco2e || 0),
    0
  );

  // Group mitigations by group field. Ungrouped mitigations bucket into "Ungrouped".
  const grouped = useMemo(() => {
    const groups = new Map<string, Mitigation[]>();
    for (const m of mitigations) {
      const key = m.group?.trim() ? m.group.trim() : "Ungrouped";
      const arr = groups.get(key) ?? [];
      arr.push(m);
      groups.set(key, arr);
    }
    return Array.from(groups.entries());
  }, [mitigations]);

  return (
    <div className={embedded ? "" : "px-12 py-6"}>
      <div className="flex items-center justify-between mb-4">
        <div>
         {!embedded && (
            <h2 className="text-2xl text-text-dark">Mitigations</h2>
          )}
          {/* <div className="text-sm text-text-faint mt-1">
            Track custom mitigations and their estimated emissions saving.
          </div> */}
        </div>
        {allowMutations && onAdd && (
          <button
            type="button"
            onClick={onAdd}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm cursor-pointer rounded-[var(--radius-3)] bg-primary text-white hover:bg-primary/90"
          >
            <span className="material-symbols-rounded text-base leading-none">
              add
            </span>
            Add mitigation
          </button>
        )}
      </div>

      {mitigations.length > 0 && (
        <div className="bg-white border border-neutral-90 rounded-[var(--radius-3)] p-5 mb-6 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide text-text-faint">
              Total estimated saving
            </div>
            <div className="text-[28px] font-bold text-text-dark leading-tight">
              {totalSaving.toFixed(2)}{" "}
              <span className="font-light">
                tCO<sub>2</sub>e
              </span>
            </div>
          </div>
          <div className="text-sm text-text-faint">
            {mitigations.length} mitigation{mitigations.length === 1 ? "" : "s"}
          </div>
        </div>
      )}

      <div className="bg-white border border-neutral-90 rounded-[var(--radius-3)]">
        <table className="w-full text-sm">
          <thead className="bg-neutral-95 text-text-base uppercase text-xs tracking-wide">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Mitigation name</th>
              <th className="text-left px-4 py-3 font-medium">Project stage</th>
              <th className="text-left px-4 py-3 font-medium">Mitigation category</th>
              <th className="text-right px-4 py-3 font-medium">
                Emissions savings (tCO<sub>2</sub>e)
              </th>
              <th className="text-left px-4 py-3 font-medium">Notes / Comments (optional)</th>
              {(allowMutations || viewOnlyInteraction) && (
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              )}
            </tr>
          </thead>
          <tbody>
            {mitigations.length === 0 ? (
              <tr className="border-t border-neutral-90">
                <td
                  colSpan={allowMutations || viewOnlyInteraction ? 7 : 6}
                  className="px-4 py-10 text-center"
                >
                  <div className="text-text-dark font-medium">No mitigations yet</div>
                  <div className="text-sm text-text-faint mt-1">
                    Get started by adding data manually.
                  </div>
                </td>
              </tr>
            ) : (
              grouped.flatMap(([_, items]) =>
                items.map((m) => {
                  return (
                    <tr
                      key={m.id}
                      className={`border-t border-neutral-90 hover:bg-neutral-98 ${viewOnlyInteraction ? "cursor-pointer" : ""
                        }`}
                      onClick={() => viewOnlyInteraction && onOpenRow?.(m)}
                      role={viewOnlyInteraction ? "button" : undefined}
                    >
                      <td className="px-4 py-3 text-text-dark">{m.name}</td>
                      <td className="px-4 py-3 text-text-base">{m.lifecyclePhaseLabel}</td>
                      <td className="px-4 py-3 text-text-base">{TYPE_LABEL[m.type]}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-text-dark">
                        {(m.estimatedSavingTco2e || 0).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-text-base">{m.notes || "—"}</td>
                      {(allowMutations || viewOnlyInteraction) && (
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex items-center gap-1 justify-end">
                            {allowMutations && (
                              <>
                                <button
                                  type="button"
                                  aria-label={`Edit ${m.name}`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onEdit?.(m);
                                  }}
                                  className="p-1 rounded hover:bg-neutral-95 text-text-base cursor-pointer"
                                >
                                  <span className="material-symbols-rounded text-[18px]">
                                    edit
                                  </span>
                                </button>
                                <button
                                  type="button"
                                  aria-label={`Delete ${m.name}`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onDelete?.(m.id);
                                  }}
                                  className="p-1 rounded hover:bg-neutral-95 text-text-base cursor-pointer"
                                >
                                  <span className="material-symbols-rounded text-[18px]">
                                    delete
                                  </span>
                                </button>
                              </>
                            )}
                            {viewOnlyInteraction && !allowMutations && (
                              <span className="material-symbols-rounded text-[18px] text-text-faint">
                                visibility
                              </span>
                            )}
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
  );
};

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
          const sumTableRows = (tableRows: any[]) =>
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
      const replaced: Record<string, any[]> = {};
      const adopted: Record<string, any[]> = {};
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
      const tables: Record<string, any[]> = {};
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
        projectId={projectId}
        jurisdictionName={jurisdictionName}
        mitigationScenarioId={wizardScenarioId}
        persistence={persistence}
        hydrateSnapshot={hydrateSnapshot}
        detailReadOnly={detailReadOnly}
        tablesCollectorRef={tablesCollectorRef}
        onPersisted={refreshMitigations}
        mitigationStageInstanceId={mitigationStageInstanceId}
        mitigationProjectOptionId={mitigationProjectOptionId}
        projectTypeName={projectTypeName}
        opsStartYear={opsStartYear}
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