import { useState, type Dispatch, type SetStateAction } from "react";
import ActivityDataService from "@/services/ActivityData.service";
import { isElectricityTable, type UploadKey } from "../stageConstants";
import type { DataEntryRow } from "../dataEntryTypes";
import type { MitigationPersistenceApi } from "../Mitigations";
import type { MitigationSubstitutionLeg } from "../mitigationConstants";
import type { MitigationRowState } from "./useMitigationTableRows";

type Params = {
  readOnly: boolean;
  projectMitigationId: string | null;
  mitigationMode: "reduction" | "substitution";
  substitutionLeg: MitigationSubstitutionLeg | null;
  tableRows: MitigationRowState;
  saveMitigationNewRow?: MitigationPersistenceApi["saveMitigationNewRow"];
  uploadMitigationTableFile?: MitigationPersistenceApi["uploadMitigationTableFile"];
  computeEmissionsForRow?: MitigationPersistenceApi["computeEmissionsForRow"];
  refreshOptionTotals?: MitigationPersistenceApi["refreshOptionTotals"];
  setInlineError: (key: UploadKey, message: string | null) => void;
};

type RowUpdater = Dispatch<SetStateAction<DataEntryRow[]>>;
type MitigationUploadKey = UploadKey;

export function useMitigationTableUploads({
  readOnly,
  projectMitigationId,
  mitigationMode,
  substitutionLeg,
  tableRows,
  saveMitigationNewRow,
  uploadMitigationTableFile,
  computeEmissionsForRow,
  refreshOptionTotals,
  setInlineError,
}: Params) {
  const [uploadTarget, setUploadTarget] = useState<MitigationUploadKey | null>(null);
  const persistLeg = mitigationMode === "substitution" ? substitutionLeg : null;

  const rowsByKey: Partial<Record<MitigationUploadKey, DataEntryRow[]>> = {
    component: tableRows.componentRows,
    bcDetailedLevel: tableRows.bcDetailedRows,
    electricity: tableRows.electricityRows,
    useB1G2: tableRows.useB1G2Rows,
    useB1G3: tableRows.useB1G3Rows,
    componentRepl: tableRows.componentReplRows,
    refurbishment: tableRows.refurbRows,
    replDetailed: tableRows.replDetailedRows,
    opEnergy: tableRows.opEnergyRows,
    opEnergyDetailed: tableRows.opEnergyDetailedRows,
    opEnergyElectricity: tableRows.opEnergyElectricityRows,
    constructionG2: tableRows.constructionG2Rows,
    constructionG3: tableRows.constructionG3Rows,
    concreteRegSimplified: tableRows.concreteRegSimplifiedRows,
  };
  const settersByKey: Partial<Record<MitigationUploadKey, RowUpdater>> = {
    component: tableRows.setComponentRows,
    bcDetailedLevel: tableRows.setBcDetailedRows,
    electricity: tableRows.setElectricityRows,
    useB1G2: tableRows.setUseB1G2Rows,
    useB1G3: tableRows.setUseB1G3Rows,
    componentRepl: tableRows.setComponentReplRows,
    refurbishment: tableRows.setRefurbRows,
    replDetailed: tableRows.setReplDetailedRows,
    opEnergy: tableRows.setOpEnergyRows,
    opEnergyDetailed: tableRows.setOpEnergyDetailedRows,
    opEnergyElectricity: tableRows.setOpEnergyElectricityRows,
    constructionG2: tableRows.setConstructionG2Rows,
    constructionG3: tableRows.setConstructionG3Rows,
    concreteRegSimplified: tableRows.setConcreteRegSimplifiedRows,
  };
  const isMitigationUploadKey = (key: string): key is MitigationUploadKey =>
    Object.keys(settersByKey).includes(key);

  const requestMitigationUpload = (key: MitigationUploadKey) => {
    if (readOnly || !projectMitigationId || !uploadMitigationTableFile) return;
    setUploadTarget(key);
  };

  const applyUploadedRows = (key: MitigationUploadKey, rows: DataEntryRow[]) => {
    settersByKey[key]?.(rows);
  };

  const appendMitigationRow = (key: string, row: DataEntryRow) => {
    if (!isMitigationUploadKey(key)) return;
    const setter = settersByKey[key];
    setter?.((rows) => [row, ...rows]);
  };

  const saveMitigationRow = (uploadKey: MitigationUploadKey) => async (draft: DataEntryRow) => {
    if (readOnly || !saveMitigationNewRow || !projectMitigationId) return true;

    const electricityKey = uploadKey === "opEnergyElectricity" ? "opEnergyElectricity" : "electricity";
    const isElectricity = isElectricityTable(uploadKey);
    const electricityRows = isElectricity ? rowsByKey[electricityKey] ?? [] : [];
    const existingSiblings = electricityRows.filter((row) => row._fromApi);

    const saved = await saveMitigationNewRow(
      uploadKey,
      projectMitigationId,
      draft,
      appendMitigationRow,
      (message) => setInlineError(uploadKey, message),
      persistLeg,
    );

    const updateElectricityRows = settersByKey[electricityKey];
    if (saved && existingSiblings.length > 0 && computeEmissionsForRow && updateElectricityRows) {
      void (async () => {
        for (const sibling of existingSiblings) {
          try {
            if (sibling.id == null) continue;
            const patch = await computeEmissionsForRow(uploadKey, sibling);
            if (!patch) continue;
            updateElectricityRows((rows) => rows.map((row) =>
              row.id === sibling.id ? { ...row, ...patch } : row,
            ));
            const raw = patch.total_emissions_tco2e ?? patch.emissions_tco2e;
            const emissions = raw === "-" || raw == null || Number.isNaN(Number(raw))
              ? null
              : Number(raw);
            const updatedRow = { ...sibling, ...patch };
            const extraFields = {
              ...updatedRow,
              location_based_tco2e: patch.location_based_tco2e ?? null,
              market_based_tco2e: patch.market_based_tco2e ?? null,
            };
            delete extraFields._fromApi;
            await ActivityDataService.updateRow(String(sibling.id), {
              quantity: Number(updatedRow.quantity_mwh ?? sibling.quantity ?? 0),
              emissions_tco2e: emissions,
              extra_fields: extraFields,
            });
          } catch (error) {
            console.warn("Mitigation: failed to recalc electricity sibling", sibling.id, error);
          }
        }
        try { await refreshOptionTotals?.(); } catch { /* retain the save result if totals refresh fails */ }
      })();
    }
    return saved;
  };

  return {
    uploadTarget,
    setUploadTarget,
    persistLeg,
    requestMitigationUpload,
    applyUploadedRows,
    saveMitigationRow,
  };
}
