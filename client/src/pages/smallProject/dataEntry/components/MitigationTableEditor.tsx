import React, { useCallback, useEffect, useMemo, useState } from "react";
import { NumericInput } from "@/components/common/NumericInput";
import TableWrapper from "@/components/common/TableWrapper";
import { componentTableConfig } from "../componentConfig";
import { componentReplacementConfig } from "../componentReplacementConfig";
import { refurbishmentTableConfig } from "../refurbishmentTableConfig";
import { opEnergyTableConfig } from "../opEnergyTableConfig";
import { constructionG2Config } from "../constructionG2Config";
import { constructionG3Config } from "../constructionG3Config";
import { electricityConfig } from "../electricityConfig";
import { createB1G2Config } from "../useB1G2Config";
import { createB1G3Config } from "../useB1G3Config";
import { concreteRegSimplifiedConfig } from "../ConcreteRegSimplifiedConfig";
import { type MitigationSubstitutionLeg } from "../mitigationConstants";
import { useLargeUserYears } from "../hooks/useLargeUserYears";
import UsersSubStage from "../UsersSubStage";
import type { DataEntryRow } from "../dataEntryTypes";
import type { MitigationLifecyclePhase, MitigationType } from "../mitigationTypes";
import type { MitigationPersistenceApi, MitigationTablesCollector, StageName } from "../Mitigations";
import { useMitigationTableRows } from "../hooks/useMitigationTableRows";
import { useMitigationTableUploads } from "../hooks/useMitigationTableUploads";
import { MitigationUploadDialog } from "./MitigationUploadDialog";
type MitigationUploadKey = React.ComponentProps<typeof TableWrapper>["uploadKey"];
type MitigationEditorValue = string | number | null | undefined;
type MitigationEditorProps = {
  value: unknown;
  onChange: (value: unknown) => void;
  onCommit: (value?: unknown) => void;
  item?: DataEntryRow;
};
type MitigationEditorColumn = {
  key?: string;
  editorType?: string;
  renderEditor?: (props: MitigationEditorProps) => React.ReactNode;
};

const MitigationCellEditor = (col: MitigationEditorColumn, props: MitigationEditorProps) => {
  const value: MitigationEditorValue = typeof props.value === "string" || typeof props.value === "number"
    ? props.value
    : null;
  if (col.editorType === "year") {
    return (
      <input
        type="number"
        className="h-10 w-full bg-white border border-border-input rounded px-2 py-1 text-sm"
        value={value ?? ""}
        onChange={(e) => props.onChange(e.target.value)}
        onBlur={() => props.onCommit(value)}
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
        value={value}
        onChange={(next) => props.onChange(next)}
        onCommit={(next) => props.onCommit(next)}
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
        value={value ?? ""}
        onChange={(e) => props.onChange(e.target.value)}
        onBlur={() => props.onCommit(value)}
        autoFocus
      />
    );
  }
  return col.renderEditor?.(props);
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

export const EmptyMitigationTables: React.FC<{
  submissionStage: StageName;
  lifecyclePhase: MitigationLifecyclePhase;
  projectId: string;
  jurisdictionName?: string | null;
  scopeKey: string;
  collectorRef?: React.MutableRefObject<MitigationTablesCollector | null>;
  hydrateTables?: Record<string, DataEntryRow[]> | null;
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

  const tableRows = useMitigationTableRows({
    submissionStage,
    lifecyclePhase,
    collectorRef,
    hydrateTables,
  });
  const {
    componentRows, setComponentRows, bcDetailedRows, setBcDetailedRows,
    electricityRows, setElectricityRows, useB1G2Rows, setUseB1G2Rows,
    useB1G3Rows, setUseB1G3Rows, componentReplRows, setComponentReplRows,
    refurbRows, setRefurbRows, replDetailedRows, setReplDetailedRows,
    opEnergyRows, setOpEnergyRows, opEnergyDetailedRows, setOpEnergyDetailedRows,
    opEnergyElectricityRows, setOpEnergyElectricityRows,
    constructionG2Rows, setConstructionG2Rows, constructionG3Rows, setConstructionG3Rows,
    concreteRegSimplifiedRows, setConcreteRegSimplifiedRows,
  } = tableRows;
  const [mitigationInlineErr, setMitigationInlineErr] = useState<
    Record<string, string | null>
  >({});

  const wrapMitigationCellChange = useCallback(
    (key: MitigationUploadKey, setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>) =>
      onCellChange?.(key, setRows, (msg: string | null) =>
        setMitigationInlineErr((e) => ({ ...e, [key]: msg })),
      ),
    [onCellChange],
  );

  const wrapMitigationRowPatch = useCallback(
    (key: MitigationUploadKey, setRows: React.Dispatch<React.SetStateAction<DataEntryRow[]>>) =>
      onRowPatch?.(key, setRows, (msg: string | null) =>
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

  const setInlineError = useCallback((key: MitigationUploadKey, message: string | null) => {
    setMitigationInlineErr((previous) => ({ ...previous, [key]: message }));
  }, []);
  const uploadActions = useMitigationTableUploads({
    readOnly,
    projectMitigationId,
    mitigationMode,
    substitutionLeg,
    tableRows,
    saveMitigationNewRow,
    uploadMitigationTableFile,
    computeEmissionsForRow,
    refreshOptionTotals: _refreshOptionTotals,
    setInlineError,
  });
  const {
    uploadTarget,
    setUploadTarget,
    persistLeg,
    requestMitigationUpload,
    applyUploadedRows,
    saveMitigationRow,
  } = uploadActions;
const mitigationUploadModal = (
  <MitigationUploadDialog
    open={uploadTarget != null}
    uploadKey={uploadTarget}
    projectId={projectId}
    projectMitigationId={projectMitigationId}
    substitutionLeg={persistLeg}
    onClose={() => setUploadTarget(null)}
    upload={async (key, mitigationId, rows, leg) => {
      if (!uploadMitigationTableFile) throw new Error("Mitigation uploads are unavailable.");
      return uploadMitigationTableFile(key, mitigationId, rows, leg);
    }}
    onUploaded={(key, rows) => {
      applyUploadedRows(key, rows);
      setMitigationInlineErr((previous) => ({ ...previous, [key]: null }));
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
    () => createB1G2Config(null, projectId).columns(),
    [projectId]
  );
  const useB1G3Columns = useMemo(() => createB1G3Config(projectId).columns(), [projectId]);
  const componentReplColumns = useMemo(
    () => componentReplacementConfig(projectId).columns(),
    [projectId]
  );
  const refurbColumns = useMemo(() => refurbishmentTableConfig(jurisdictionName).columns(), [jurisdictionName]);
  const opEnergyColumns = useMemo(() => opEnergyTableConfig(projectId).columns(), [projectId]);
  const replDetailedColumns = useMemo(
    () => createB1G3Config(projectId).columns(),
    [projectId]
  );
  const opEnergyDetailedColumns = useMemo(
    () => createB1G3Config(projectId, ["Fuels", "Water"]).columns(),
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

  const renderEditor = (col: MitigationEditorColumn, props: MitigationEditorProps) =>
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
          onNewRowSave={saveMitigationRow("useB1G2")}
          onCellChange={wrapMitigationCellChange("useB1G2", setUseB1G2Rows)}
          onRowPatch={wrapMitigationRowPatch("useB1G2", setUseB1G2Rows)}
          accordionKey="useB1G2"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("useB1G3")}
          onCellChange={wrapMitigationCellChange("useB1G3", setUseB1G3Rows)}
          onRowPatch={wrapMitigationRowPatch("useB1G3", setUseB1G3Rows)}
          accordionKey="useB1G3"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("componentRepl")}
          onCellChange={wrapMitigationCellChange("componentRepl", setComponentReplRows)}
          onRowPatch={wrapMitigationRowPatch("componentRepl", setComponentReplRows)}
          accordionKey="componentRepl"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("refurbishment")}
          onCellChange={wrapMitigationCellChange("refurbishment", setRefurbRows)}
          onRowPatch={wrapMitigationRowPatch("refurbishment", setRefurbRows)}
          accordionKey="refurbishment"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("replDetailed")}
          onCellChange={wrapMitigationCellChange("replDetailed", setReplDetailedRows)}
          onRowPatch={wrapMitigationRowPatch("replDetailed", setReplDetailedRows)}
          accordionKey="replDetailed"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("opEnergy")}
          onCellChange={wrapMitigationCellChange("opEnergy", setOpEnergyRows)}
          onRowPatch={wrapMitigationRowPatch("opEnergy", setOpEnergyRows)}
          accordionKey="opEnergy"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("opEnergyDetailed")}
          onCellChange={wrapMitigationCellChange("opEnergyDetailed", setOpEnergyDetailedRows)}
          onRowPatch={wrapMitigationRowPatch("opEnergyDetailed", setOpEnergyDetailedRows)}
          accordionKey="opEnergyDetailed"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("opEnergyElectricity")}
          onCellChange={wrapMitigationCellChange("opEnergyElectricity", setOpEnergyElectricityRows)}
          onRowPatch={wrapMitigationRowPatch("opEnergyElectricity", setOpEnergyElectricityRows)}
          accordionKey="opEnergyElectricity"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("component")}
          onCellChange={wrapMitigationCellChange("component", setComponentRows)}
          onRowPatch={wrapMitigationRowPatch("component", setComponentRows)}
          accordionKey="component"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("bcDetailedLevel")}
          onCellChange={wrapMitigationCellChange("bcDetailedLevel", setBcDetailedRows)}
          onRowPatch={wrapMitigationRowPatch("bcDetailedLevel", setBcDetailedRows)}
          accordionKey="bcDetailedLevel"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("electricity")}
          onCellChange={wrapMitigationCellChange("electricity", setElectricityRows)}
          onRowPatch={wrapMitigationRowPatch("electricity", setElectricityRows)}
          accordionKey="electricity"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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
            onNewRowSave={saveMitigationRow("concreteRegSimplified")}
            onCellChange={wrapMitigationCellChange("concreteRegSimplified", setConcreteRegSimplifiedRows)}
            onRowPatch={wrapMitigationRowPatch("concreteRegSimplified", setConcreteRegSimplifiedRows)}
            accordionKey="concreteRegSimplified"
            accordionState={accordionState}
            setAccordionState={setAccordionState}
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
        onNewRowSave={saveMitigationRow("constructionG2")}
        onCellChange={wrapMitigationCellChange("constructionG2", setConstructionG2Rows)}
        onRowPatch={wrapMitigationRowPatch("constructionG2", setConstructionG2Rows)}
        accordionKey="constructionG2"
        accordionState={accordionState}
        setAccordionState={setAccordionState}
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
        onNewRowSave={saveMitigationRow("constructionG3")}
        onCellChange={wrapMitigationCellChange("constructionG3", setConstructionG3Rows)}
        onRowPatch={wrapMitigationRowPatch("constructionG3", setConstructionG3Rows)}
        accordionKey="constructionG3"
        accordionState={accordionState}
        setAccordionState={setAccordionState}
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
        onNewRowSave={saveMitigationRow("electricity")}
        onCellChange={wrapMitigationCellChange("electricity", setElectricityRows)}
        onRowPatch={wrapMitigationRowPatch("electricity", setElectricityRows)}
        accordionKey="electricity"
        accordionState={accordionState}
        setAccordionState={setAccordionState}
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
          onNewRowSave={saveMitigationRow("concreteRegSimplified")}
          onCellChange={wrapMitigationCellChange("concreteRegSimplified", setConcreteRegSimplifiedRows)}
          onRowPatch={wrapMitigationRowPatch("concreteRegSimplified", setConcreteRegSimplifiedRows)}
          accordionKey="concreteRegSimplified"
          accordionState={accordionState}
          setAccordionState={setAccordionState}
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

