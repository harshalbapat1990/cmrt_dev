import { useCallback, useState } from "react";
import { ConcreteRegisterService } from "@/services/ConcreteRegister.service";
import { getCarbonIntensity, getEpdEmissions, getMixEmissions } from "../concreteRegisterCalculations";
import { CONCRETE_STRENGTHS, MIX_TYPE_OPTIONS, type EpdRow, type MaterialRow, type MixRow, type SimplifiedRow } from "../concreteRegisterTypes";

type Params = {
  projectId: string;
  setSimplifiedRows: React.Dispatch<React.SetStateAction<SimplifiedRow[]>>;
  mixRows: MixRow[];
  setMixRows: React.Dispatch<React.SetStateAction<MixRow[]>>;
  materialsMap: Record<string, MaterialRow[]>;
  setMaterialsMap: React.Dispatch<React.SetStateAction<Record<string, MaterialRow[]>>>;
  setEpdRows: React.Dispatch<React.SetStateAction<EpdRow[]>>;
};

const newId = () => crypto.randomUUID();

export function useConcreteRegisterActions({
  projectId, setSimplifiedRows, setMixRows, materialsMap, setMaterialsMap, setEpdRows,
}: Params) {
  const [simplifiedDraft, setSimplifiedDraft] = useState<SimplifiedRow | null>(null);

  const addSimplifiedRow = () => {
    if (simplifiedDraft) return;
    setSimplifiedDraft({
      id: newId(), mixType: MIX_TYPE_OPTIONS[0].value,
      strengthMpa: String(CONCRETE_STRENGTHS[0]), scmPct: null,
      volumeM3: null, notes: "", emissions_tco2e: 0,
    });
  };
  const updateSimplifiedDraft = <K extends keyof SimplifiedRow>(key: K, value: SimplifiedRow[K]) => {
    setSimplifiedDraft((current) => current ? { ...current, [key]: value } : current);
  };
  const saveSimplifiedDraft = useCallback(async () => {
    if (!simplifiedDraft) return;
    try {
      const result = await ConcreteRegisterService.createMix({
        project_id: projectId, method: "simplified", mix_type: simplifiedDraft.mixType,
        strength_mpa: Number(simplifiedDraft.strengthMpa), scm_pct: simplifiedDraft.scmPct,
        volume_m3: simplifiedDraft.volumeM3, emissions_tco2e: 0, notes: simplifiedDraft.notes,
      });
      setSimplifiedRows((rows) => [...rows, {
        id: result.id, mixType: result.mix_type ?? simplifiedDraft.mixType,
        strengthMpa: result.strength_mpa !== null ? String(result.strength_mpa) : simplifiedDraft.strengthMpa,
        scmPct: result.scm_pct !== null ? Number(result.scm_pct) : null,
        volumeM3: result.volume_m3 !== null ? Number(result.volume_m3) : null,
        notes: result.notes ?? "", emissions_tco2e: Number(result.emissions_tco2e),
      }]);
      setSimplifiedDraft(null);
    } catch (error) { console.error("Failed to create simplified mix:", error); }
  }, [projectId, setSimplifiedRows, simplifiedDraft]);
  const updateSimplifiedRow = <K extends keyof SimplifiedRow>(idx: number, key: K, value: SimplifiedRow[K]) => {
    setSimplifiedRows((rows) => rows.map((row, index) => index === idx ? { ...row, [key]: value } : row));
  };
  const syncSimplifiedRow = useCallback(async (row: SimplifiedRow) => {
    try {
      const result = await ConcreteRegisterService.updateMix(row.id, {
        mix_type: row.mixType, strength_mpa: Number(row.strengthMpa),
        scm_pct: row.scmPct, volume_m3: row.volumeM3, notes: row.notes,
      });
      setSimplifiedRows((rows) => rows.map((current) => current.id === row.id
        ? { ...current, emissions_tco2e: Number(result.emissions_tco2e) } : current));
    } catch (error) { console.error("Failed to update simplified mix:", error); }
  }, [setSimplifiedRows]);
  const deleteSimplifiedRow = useCallback(async (id: string) => {
    try {
      await ConcreteRegisterService.deleteMix(id);
      setSimplifiedRows((rows) => rows.filter((row) => row.id !== id));
    } catch (error) { console.error("Failed to delete simplified mix:", error); }
  }, [setSimplifiedRows]);
  const getSimplifiedEmissions = (row: SimplifiedRow): number | null => row.emissions_tco2e;

  const addMixRow = useCallback(async () => {
    try {
      const result = await ConcreteRegisterService.createMix({
        project_id: projectId, method: "mix_design", mix_type: MIX_TYPE_OPTIONS[0].value,
        strength_mpa: CONCRETE_STRENGTHS[0], emissions_tco2e: 0,
      });
      setMixRows((rows) => [...rows, {
        id: result.id, mixId: result.mix_id_label ?? "", mixType: result.mix_type ?? MIX_TYPE_OPTIONS[0].value,
        strengthMpa: result.strength_mpa !== null ? String(result.strength_mpa) : String(CONCRETE_STRENGTHS[0]),
        volumeM3: null, notes: "", expanded: false,
      }]);
      setMaterialsMap((current) => ({ ...current, [result.id]: [] }));
    } catch (error) { console.error("Failed to create mix design row:", error); }
  }, [projectId, setMaterialsMap, setMixRows]);
  const updateMixRow = <K extends keyof MixRow>(id: string, key: K, value: MixRow[K]) => {
    setMixRows((rows) => rows.map((row) => row.id === id ? { ...row, [key]: value } : row));
  };
  const syncMixRow = useCallback(async (row: MixRow) => {
    try {
      await ConcreteRegisterService.updateMix(row.id, {
        mix_id_label: row.mixId, mix_type: row.mixType, strength_mpa: Number(row.strengthMpa),
        volume_m3: row.volumeM3, notes: row.notes,
      });
    } catch (error) { console.error("Failed to update mix design row:", error); }
  }, []);
  const deleteMixRow = useCallback(async (id: string) => {
    try {
      await ConcreteRegisterService.deleteMix(id);
      setMixRows((rows) => rows.filter((row) => row.id !== id));
      setMaterialsMap((current) => { const next = { ...current }; delete next[id]; return next; });
    } catch (error) { console.error("Failed to delete mix design row:", error); }
  }, [setMaterialsMap, setMixRows]);
  const toggleMixExpanded = (id: string) => setMixRows((rows) => rows.map((row) => row.id === id ? { ...row, expanded: !row.expanded } : row));

  const addMaterial = useCallback(async (mixId: string) => {
    try {
      const result = await ConcreteRegisterService.createMaterial(mixId, {
        concrete_mix_id: mixId, material_name: "", quantity_kg_m3: null, carbon_factor: null,
      });
      setMaterialsMap((current) => ({ ...current, [mixId]: [...(current[mixId] ?? []), {
        id: result.id, materialName: result.material_name,
        quantityKgM3: result.quantity_kg_m3 !== null ? Number(result.quantity_kg_m3) : null,
        carbonFactor: result.carbon_factor !== null ? Number(result.carbon_factor) : null,
      }] }));
    } catch (error) { console.error("Failed to add material:", error); }
  }, [setMaterialsMap]);
  const updateMaterial = <K extends keyof MaterialRow>(mixId: string, matId: string, key: K, value: MaterialRow[K]) => {
    setMaterialsMap((current) => ({ ...current, [mixId]: (current[mixId] ?? []).map((row) => row.id === matId ? { ...row, [key]: value } : row) }));
  };
  const syncMaterial = useCallback(async (material: MaterialRow) => {
    try {
      await ConcreteRegisterService.updateMaterial(material.id, {
        material_name: material.materialName, quantity_kg_m3: material.quantityKgM3,
        carbon_factor: material.carbonFactor,
      });
    } catch (error) { console.error("Failed to update material:", error); }
  }, []);
  const deleteMaterial = useCallback(async (mixId: string, materialId: string) => {
    try {
      await ConcreteRegisterService.deleteMaterial(materialId);
      setMaterialsMap((current) => ({ ...current, [mixId]: (current[mixId] ?? []).filter((row) => row.id !== materialId) }));
    } catch (error) { console.error("Failed to delete material:", error); }
  }, [setMaterialsMap]);
  const getMixEmissionsForRow = (row: MixRow) => getMixEmissions(row, materialsMap[row.id]);
  const getCarbonIntensityForMix = (mixId: string) => getCarbonIntensity(materialsMap[mixId]);

  const addEpdRow = useCallback(async () => {
    try {
      const result = await ConcreteRegisterService.createMix({ project_id: projectId, method: "epd_pcf", emissions_tco2e: 0 });
      setEpdRows((rows) => [...rows, {
        id: result.id, mixId: result.mix_id_label ?? "", gwpA1A3: null,
        volumeM3: null, notes: "", emissions_tco2e: Number(result.emissions_tco2e),
      }]);
    } catch (error) { console.error("Failed to create EPD row:", error); }
  }, [projectId, setEpdRows]);
  const updateEpdRow = <K extends keyof EpdRow>(id: string, key: K, value: EpdRow[K]) => {
    setEpdRows((rows) => rows.map((row) => row.id === id ? { ...row, [key]: value } : row));
  };
  const syncEpdRow = useCallback(async (row: EpdRow) => {
    try {
      const result = await ConcreteRegisterService.updateMix(row.id, {
        mix_id_label: row.mixId, gwp_a1a3: row.gwpA1A3, volume_m3: row.volumeM3, notes: row.notes,
      });
      setEpdRows((rows) => rows.map((current) => current.id === row.id
        ? { ...current, emissions_tco2e: Number(result.emissions_tco2e) } : current));
    } catch (error) { console.error("Failed to update EPD row:", error); }
  }, [setEpdRows]);
  const deleteEpdRow = useCallback(async (id: string) => {
    try {
      await ConcreteRegisterService.deleteMix(id);
      setEpdRows((rows) => rows.filter((row) => row.id !== id));
    } catch (error) { console.error("Failed to delete EPD row:", error); }
  }, [setEpdRows]);
  const getEpdEmissionsForRow = (row: EpdRow) => getEpdEmissions(row);

  return {
    simplifiedDraft, addSimplifiedRow, updateSimplifiedDraft,
    saveSimplifiedDraft, cancelSimplifiedDraft: () => setSimplifiedDraft(null),
    updateSimplifiedRow, syncSimplifiedRow, deleteSimplifiedRow, getSimplifiedEmissions,
    addMixRow, updateMixRow, syncMixRow, deleteMixRow, toggleMixExpanded,
    addMaterial, updateMaterial, syncMaterial, deleteMaterial,
    getCarbonIntensity: getCarbonIntensityForMix, getMixEmissions: getMixEmissionsForRow,
    addEpdRow, updateEpdRow, syncEpdRow, deleteEpdRow, getEpdEmissions: getEpdEmissionsForRow,
  };
}
