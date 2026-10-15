import { UploadModal } from "@/pages/dummy-table/UploadModal";
import { parseFileToRows } from "@/utils/parseFileToRows";
import { normalizeValidationRules, validateRows } from "@/utils/ValidateRows";
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
import type { MitigationSubstitutionLeg } from "../mitigationConstants";
import type { DataEntryRow } from "../dataEntryTypes";
import type { UploadKey } from "../stageConstants";
import { toDataEntryRows } from "../dataEntryValidation";

function resolveUploadConfig(uploadKey: UploadKey, projectId: string) {
  switch (uploadKey) {
    case "component": return componentTableConfig(projectId);
    case "bcDetailedLevel": return constructionG3Config(projectId);
    case "electricity": return electricityConfig(projectId);
    case "concreteRegSimplified": return concreteRegSimplifiedConfig();
    case "constructionG2": return constructionG2Config(projectId);
    case "constructionG3": return constructionG3Config(projectId);
    case "useB1G2": return createB1G2Config(null, projectId);
    case "useB1G3": return createB1G3Config(projectId);
    case "componentRepl": return componentReplacementConfig(projectId);
    case "refurbishment": return refurbishmentTableConfig(null);
    case "replDetailed": return createB1G3Config(projectId);
    case "opEnergy": return opEnergyTableConfig(projectId);
    case "opEnergyDetailed": return createB1G3Config(projectId, ["Fuels", "Water"]);
    case "opEnergyElectricity": return electricityConfig(projectId);
    default: throw new Error(`Unsupported mitigation upload key: ${uploadKey}`);
  }
}

interface Props {
  open: boolean;
  uploadKey: UploadKey | null;
  projectId: string;
  projectMitigationId: string | null;
  substitutionLeg: MitigationSubstitutionLeg | null;
  onClose: () => void;
  upload: (
    key: UploadKey,
    projectMitigationId: string,
    rows: DataEntryRow[],
    substitutionLeg: MitigationSubstitutionLeg | null,
  ) => Promise<{ rows: DataEntryRow[] }>;
  onUploaded: (key: UploadKey, rows: DataEntryRow[]) => void;
}

/** Owns mitigation CSV/XLSX parsing, validation, and upload dialog behavior. */
export function MitigationUploadDialog({
  open,
  uploadKey,
  projectId,
  projectMitigationId,
  substitutionLeg,
  onClose,
  upload,
  onUploaded,
}: Props) {
  return (
    <UploadModal<DataEntryRow>
      open={open}
      onClose={onClose}
      parseFile={async (file) => {
        if (!uploadKey) return [];
        const config = resolveUploadConfig(uploadKey, projectId);
        return toDataEntryRows(await parseFileToRows(file, config.fileHeaders, ["quantity"], {}));
      }}
      validateRows={async (parsed) => {
        if (!uploadKey) return { validRows: [], errors: [] };
        if (parsed.length === 0) {
          return { validRows: [], errors: ["The selected file contains no data rows."] };
        }
        const config = resolveUploadConfig(uploadKey, projectId);
        const rules = normalizeValidationRules(config.rules || []);
        const result = await validateRows(parsed, rules);
        return { validRows: toDataEntryRows(result.validRows), errors: result.errors };
      }}
      onSuccess={async (validRows) => {
        if (!uploadKey || !projectMitigationId) return;
        try {
          const { rows } = await upload(uploadKey, projectMitigationId, validRows, substitutionLeg);
          onUploaded(uploadKey, rows);
        } catch (error: unknown) {
          console.warn("Mitigation bulk upload failed:", error);
          throw new Error(
            error instanceof Error && error.message
              ? error.message
              : "Bulk upload failed. Please check uploaded data.",
          );
        }
      }}
    />
  );
}
