import React, { useState, useEffect, useCallback } from "react";
import { formatDisplayNumber } from "@/utils/utils";
import { SelectListbox } from "@/components/common/Select";
import { NumericInput } from "@/components/common/NumericInput";
import Download from "@/assets/icons/download.svg";
import UploadFile from "@/assets/icons/upload_file.svg";
import AddIcon from "@/assets/icons/add.svg";
import {
  ConcreteRegisterService,
  type ConcreteMixOut,
} from "@/services/ConcreteRegister.service";

export const CONCRETE_STRENGTHS = [5, 10, 15, 20, 25, 32, 40, 50, 65, 80, 100];

export const MIX_TYPE_OPTIONS = [
  { label: "Ready-mix", value: "READY_MIX" },
  { label: "Precast", value: "PRECAST" },
];

const REGISTER_TABS = ["Simplified", "Detailed"] as const;
const DETAILED_SUBTABS = ["Mix Design", "EPD / PCF"] as const;

const STRENGTH_OPTIONS = CONCRETE_STRENGTHS.map((s) => ({
  label: `${s} MPa`,
  value: String(s),
}));

export type ConcreteRegisterProps = {
  projectId: string;
  readOnly?: boolean;
};

type RegisterTab = (typeof REGISTER_TABS)[number];
type DetailedSubTab = (typeof DETAILED_SUBTABS)[number];

interface SimplifiedRow {
  id: string;
  mixType: string;
  strengthMpa: string;
  scmPct: number | null;
  volumeM3: number | null;
  notes: string;
  emissions_tco2e: number;
}

interface MixRow {
  id: string;
  mixId: string;
  mixType: string;
  strengthMpa: string;
  volumeM3: number | null;
  notes: string;
  expanded: boolean;
}

interface MaterialRow {
  id: string;
  materialName: string;
  quantityKgM3: number | null;
  carbonFactor: number | null;
}

interface EpdRow {
  id: string;
  mixId: string;
  gwpA1A3: number | null;
  volumeM3: number | null;
  notes: string;
  emissions_tco2e: number;
}

function newId(): string {
  return crypto.randomUUID();
}

function fmtEmissions(val: number | null): string {
  return formatDisplayNumber(val, { decimalsBelowThreshold: 4, threshold: Number.MAX_SAFE_INTEGER });
}

const ConcreteRegister: React.FC<ConcreteRegisterProps> = ({ projectId, readOnly = false }) => {
  const [open, setOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<RegisterTab>("Simplified");
  const [detailedSubTab, setDetailedSubTab] = useState<DetailedSubTab>("Mix Design");
  const [loading, setLoading] = useState(false);

  const [simplifiedRows, setSimplifiedRows] = useState<SimplifiedRow[]>([]);
  const [simplifiedDraft, setSimplifiedDraft] = useState<SimplifiedRow | null>(null);

  const [mixRows, setMixRows] = useState<MixRow[]>([]);
  const [materialsMap, setMaterialsMap] = useState<Record<string, MaterialRow[]>>({});

  const [epdRows, setEpdRows] = useState<EpdRow[]>([]);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    ConcreteRegisterService.listMixes(projectId)
      .then((mixes: ConcreteMixOut[]) => {
        const simplified: SimplifiedRow[] = [];
        const mix: MixRow[] = [];
        const matMap: Record<string, MaterialRow[]> = {};
        const epd: EpdRow[] = [];

        for (const m of mixes) {
          if (m.method === "simplified") {
            simplified.push({
              id: m.id,
              mixType: m.mix_type ?? MIX_TYPE_OPTIONS[0].value,
              strengthMpa:
                m.strength_mpa !== null
                  ? String(m.strength_mpa)
                  : String(CONCRETE_STRENGTHS[0]),
              scmPct: m.scm_pct !== null ? Number(m.scm_pct) : null,
              volumeM3: m.volume_m3 !== null ? Number(m.volume_m3) : null,
              notes: m.notes ?? "",
              emissions_tco2e: Number(m.emissions_tco2e),
            });
          } else if (m.method === "mix_design") {
            mix.push({
              id: m.id,
              mixId: m.mix_id_label ?? "",
              mixType: m.mix_type ?? MIX_TYPE_OPTIONS[0].value,
              strengthMpa:
                m.strength_mpa !== null
                  ? String(m.strength_mpa)
                  : String(CONCRETE_STRENGTHS[0]),
              volumeM3: m.volume_m3 !== null ? Number(m.volume_m3) : null,
              notes: m.notes ?? "",
              expanded: false,
            });
            matMap[m.id] = m.materials.map((mat) => ({
              id: mat.id,
              materialName: mat.material_name,
              quantityKgM3:
                mat.quantity_kg_m3 !== null ? Number(mat.quantity_kg_m3) : null,
              carbonFactor:
                mat.carbon_factor !== null ? Number(mat.carbon_factor) : null,
            }));
          } else if (m.method === "epd_pcf") {
            epd.push({
              id: m.id,
              mixId: m.mix_id_label ?? "",
              gwpA1A3: m.gwp_a1a3 !== null ? Number(m.gwp_a1a3) : null,
              volumeM3: m.volume_m3 !== null ? Number(m.volume_m3) : null,
              notes: m.notes ?? "",
              emissions_tco2e: Number(m.emissions_tco2e),
            });
          }
        }

        setSimplifiedRows(simplified);
        setMixRows(mix);
        setMaterialsMap(matMap);
        setEpdRows(epd);
      })
      .catch((err: unknown) => console.error("Failed to load concrete register:", err))
      .finally(() => setLoading(false));
  }, [projectId]);


  const addSimplifiedRow = () => {
    if (simplifiedDraft) return;
    setSimplifiedDraft({
      id: newId(),
      mixType: MIX_TYPE_OPTIONS[0].value,
      strengthMpa: String(CONCRETE_STRENGTHS[0]),
      scmPct: null,
      volumeM3: null,
      notes: "",
      emissions_tco2e: 0,
    });
  };

  const updateSimplifiedDraft = <K extends keyof SimplifiedRow>(
    key: K,
    value: SimplifiedRow[K],
  ) => {
    setSimplifiedDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const saveSimplifiedDraft = useCallback(async () => {
    if (!simplifiedDraft) return;
    try {
      const result = await ConcreteRegisterService.createMix({
        project_id: projectId,
        method: "simplified",
        mix_type: simplifiedDraft.mixType,
        strength_mpa: Number(simplifiedDraft.strengthMpa),
        scm_pct: simplifiedDraft.scmPct,
        volume_m3: simplifiedDraft.volumeM3,
        emissions_tco2e: 0,
        notes: simplifiedDraft.notes,
      });
      setSimplifiedRows((prev) => [
        ...prev,
        {
          id: result.id,
          mixType: result.mix_type ?? simplifiedDraft.mixType,
          strengthMpa:
            result.strength_mpa !== null
              ? String(result.strength_mpa)
              : simplifiedDraft.strengthMpa,
          scmPct: result.scm_pct !== null ? Number(result.scm_pct) : null,
          volumeM3: result.volume_m3 !== null ? Number(result.volume_m3) : null,
          notes: result.notes ?? "",
          emissions_tco2e: Number(result.emissions_tco2e),
        },
      ]);
      setSimplifiedDraft(null);
    } catch (err) {
      console.error("Failed to create simplified mix:", err);
    }
  }, [simplifiedDraft, projectId]);

  const cancelSimplifiedDraft = () => setSimplifiedDraft(null);

  const updateSimplifiedRow = <K extends keyof SimplifiedRow>(
    idx: number,
    key: K,
    value: SimplifiedRow[K],
  ) => {
    setSimplifiedRows((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], [key]: value };
      return next;
    });
  };

  const syncSimplifiedRow = useCallback(async (row: SimplifiedRow) => {
    try {
      const result = await ConcreteRegisterService.updateMix(row.id, {
        mix_type: row.mixType,
        strength_mpa: Number(row.strengthMpa),
        scm_pct: row.scmPct,
        volume_m3: row.volumeM3,
        notes: row.notes,
      });
      setSimplifiedRows((prev) =>
        prev.map((r) =>
          r.id === row.id
            ? { ...r, emissions_tco2e: Number(result.emissions_tco2e) }
            : r,
        ),
      );
    } catch (err) {
      console.error("Failed to update simplified mix:", err);
    }
  }, []);

  const deleteSimplifiedRow = useCallback(async (id: string) => {
    try {
      await ConcreteRegisterService.deleteMix(id);
      setSimplifiedRows((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      console.error("Failed to delete simplified mix:", err);
    }
  }, []);

  const getSimplifiedEmissions = (row: SimplifiedRow): number | null =>
    row.emissions_tco2e;

  const addMixRow = useCallback(async () => {
    try {
      const result = await ConcreteRegisterService.createMix({
        project_id: projectId,
        method: "mix_design",
        mix_type: MIX_TYPE_OPTIONS[0].value,
        strength_mpa: CONCRETE_STRENGTHS[0],
        emissions_tco2e: 0,
      });
      setMixRows((prev) => [
        ...prev,
        {
          id: result.id,
          mixId: result.mix_id_label ?? "",
          mixType: result.mix_type ?? MIX_TYPE_OPTIONS[0].value,
          strengthMpa:
            result.strength_mpa !== null
              ? String(result.strength_mpa)
              : String(CONCRETE_STRENGTHS[0]),
          volumeM3: null,
          notes: "",
          expanded: false,
        },
      ]);
      setMaterialsMap((prev) => ({ ...prev, [result.id]: [] }));
    } catch (err) {
      console.error("Failed to create mix design row:", err);
    }
  }, [projectId]);

  const updateMixRow = <K extends keyof MixRow>(id: string, key: K, value: MixRow[K]) => {
    setMixRows((prev) => prev.map((r) => (r.id === id ? { ...r, [key]: value } : r)));
  };

  const syncMixRow = useCallback(async (row: MixRow) => {
    try {
      await ConcreteRegisterService.updateMix(row.id, {
        mix_id_label: row.mixId,
        mix_type: row.mixType,
        strength_mpa: Number(row.strengthMpa),
        volume_m3: row.volumeM3,
        notes: row.notes,
      });
    } catch (err) {
      console.error("Failed to update mix design row:", err);
    }
  }, []);

  const deleteMixRow = useCallback(async (id: string) => {
    try {
      await ConcreteRegisterService.deleteMix(id);
      setMixRows((prev) => prev.filter((r) => r.id !== id));
      setMaterialsMap((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } catch (err) {
      console.error("Failed to delete mix design row:", err);
    }
  }, []);

  const toggleMixExpanded = (id: string) => {
    setMixRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, expanded: !r.expanded } : r)),
    );
  };

  const addMaterial = useCallback(async (mixId: string) => {
    try {
      const result = await ConcreteRegisterService.createMaterial(mixId, {
        concrete_mix_id: mixId,
        material_name: "",
        quantity_kg_m3: null,
        carbon_factor: null,
      });
      setMaterialsMap((prev) => ({
        ...prev,
        [mixId]: [
          ...(prev[mixId] ?? []),
          {
            id: result.id,
            materialName: result.material_name,
            quantityKgM3:
              result.quantity_kg_m3 !== null ? Number(result.quantity_kg_m3) : null,
            carbonFactor:
              result.carbon_factor !== null ? Number(result.carbon_factor) : null,
          },
        ],
      }));
    } catch (err) {
      console.error("Failed to add material:", err);
    }
  }, []);

  const updateMaterial = <K extends keyof MaterialRow>(
    mixId: string,
    matId: string,
    key: K,
    value: MaterialRow[K],
  ) => {
    setMaterialsMap((prev) => ({
      ...prev,
      [mixId]: (prev[mixId] ?? []).map((m) =>
        m.id === matId ? { ...m, [key]: value } : m,
      ),
    }));
  };

  const syncMaterial = useCallback(async (mat: MaterialRow) => {
    try {
      await ConcreteRegisterService.updateMaterial(mat.id, {
        material_name: mat.materialName,
        quantity_kg_m3: mat.quantityKgM3,
        carbon_factor: mat.carbonFactor,
      });
    } catch (err) {
      console.error("Failed to update material:", err);
    }
  }, []);

  const deleteMaterial = useCallback(async (mixId: string, matId: string) => {
    try {
      await ConcreteRegisterService.deleteMaterial(matId);
      setMaterialsMap((prev) => ({
        ...prev,
        [mixId]: (prev[mixId] ?? []).filter((m) => m.id !== matId),
      }));
    } catch (err) {
      console.error("Failed to delete material:", err);
    }
  }, []);

  const getCarbonIntensity = (mixId: string): number | null => {
    const mats = materialsMap[mixId] ?? [];
    if (mats.length === 0) return null;
    return mats.reduce<number | null>((acc, m) => {
      if (m.quantityKgM3 === null || m.carbonFactor === null) return acc;
      return (acc ?? 0) + m.quantityKgM3 * m.carbonFactor;
    }, null);
  };

  const getMixEmissions = (row: MixRow): number | null => {
    const ci = getCarbonIntensity(row.id);
    if (ci === null || row.volumeM3 === null) return null;
    return (row.volumeM3 * ci) / 1000;
  };

  const addEpdRow = useCallback(async () => {
    try {
      const result = await ConcreteRegisterService.createMix({
        project_id: projectId,
        method: "epd_pcf",
        emissions_tco2e: 0,
      });
      setEpdRows((prev) => [
        ...prev,
        {
          id: result.id,
          mixId: result.mix_id_label ?? "",
          gwpA1A3: null,
          volumeM3: null,
          notes: "",
          emissions_tco2e: Number(result.emissions_tco2e),
        },
      ]);
    } catch (err) {
      console.error("Failed to create EPD row:", err);
    }
  }, [projectId]);

  const updateEpdRow = <K extends keyof EpdRow>(id: string, key: K, value: EpdRow[K]) => {
    setEpdRows((prev) => prev.map((r) => (r.id === id ? { ...r, [key]: value } : r)));
  };

  const syncEpdRow = useCallback(async (row: EpdRow) => {
    try {
      const result = await ConcreteRegisterService.updateMix(row.id, {
        mix_id_label: row.mixId,
        gwp_a1a3: row.gwpA1A3,
        volume_m3: row.volumeM3,
        notes: row.notes,
      });
      setEpdRows((prev) =>
        prev.map((r) =>
          r.id === row.id
            ? { ...r, emissions_tco2e: Number(result.emissions_tco2e) }
            : r,
        ),
      );
    } catch (err) {
      console.error("Failed to update EPD row:", err);
    }
  }, []);

  const deleteEpdRow = useCallback(async (id: string) => {
    try {
      await ConcreteRegisterService.deleteMix(id);
      setEpdRows((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      console.error("Failed to delete EPD row:", err);
    }
  }, []);

  const getEpdEmissions = (row: EpdRow): number | null => {
    if (row.gwpA1A3 === null || row.volumeM3 === null) return null;
    return (row.volumeM3 * row.gwpA1A3) / 1000;
  };

  const cellCls = "px-3 py-2 border-b border-neutral-90 align-top";
  const headCls =
    "bg-neutral-95 text-text-faint text-xs uppercase px-3 py-2 text-left whitespace-nowrap";

    return (
    <div className="space-y-8 mx-12 mb-12 bg-white p-6 border border-neutral-90 rounded-[var(--radius-3)]">
      <div className="flex items-center justify-between mb-4">
        <div className="text-2xl font-light text-text-dark">
          Concrete register (grade 3/4)
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="w-5 h-5 inline-flex items-center cursor-pointer justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded"
          aria-expanded={open}
        >
          <span className="material-symbols-rounded">
            {open ? "keyboard_arrow_up" : "keyboard_arrow_down"}
          </span>
        </button>
      </div>

      {open && (
        <div>
          {loading && (
            <div className="text-sm text-text-faint py-4">Loading&hellip;</div>
          )}
          <div className="flex border-b border-neutral-90 mb-4">
            {REGISTER_TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={[
                  "px-4 py-2 text-sm font-medium cursor-pointer focus:outline-none",
                  activeTab === tab
                    ? "border-b-2 border-primary text-primary"
                    : "text-text-faint hover:text-text-base",
                ].join(" ")}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === "Simplified" && (
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mt-4 mb-5 gap-4">
                {!readOnly && (
                  <div className="flex flex-wrap gap-6 text-primary text-sm">
                    <button type="button" className="flex items-center gap-1 hover:bg-neutral-90 px-4 py-2">
                      <img src={Download} alt="" className="h-5 w-5" />
                      <span className="font-medium">{simplifiedRows.length ? "Export to Excel" : "Download blank template"}</span>
                    </button>
                    <button type="button" className="flex items-center gap-1 hover:bg-neutral-90 px-4 py-2">
                      <img src={UploadFile} alt="" className="h-5 w-5" />
                      <span className="font-medium">Upload file</span>
                    </button>
                    <button
                      type="button"
                      onClick={addSimplifiedRow}
                      disabled={!!simplifiedDraft}
                      className="flex items-center gap-1 cursor-pointer hover:bg-neutral-90 px-4 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <img src={AddIcon} alt="" className="h-5 w-5" />
                      <span className="font-medium">Add row</span>
                    </button>
                  </div>
                )}
              </div>
              <table className="border border-neutral-90 w-full text-sm">
                <thead>
                  <tr>
                    <th className={headCls}>Mix Type</th>
                    <th className={headCls}>Strength (MPa)</th>
                    <th className={headCls}>SCM Content (%)</th>
                    <th className={headCls}>Volume (m&#179;)</th>
                    <th className={headCls}>Emissions (tCO&#8322;e)</th>
                    <th className={headCls}>Notes</th>
                    <th className={`${headCls} w-20`} />
                  </tr>
                </thead>
                <tbody>
                  {simplifiedRows.length === 0 && !simplifiedDraft && (
                    <tr>
                      <td colSpan={7} className="px-4 py-10 text-center text-neutral-90">
                        <div className="text-base font-medium">No data yet</div>
                        <div className="text-sm">Get started by adding data manually or uploading a file</div>
                      </td>
                    </tr>
                  )}
                  {simplifiedRows.map((row, idx) => {
                    const emissions = getSimplifiedEmissions(row);
                    return (
                      <tr key={row.id}>
                        <td className={cellCls}>
                          {readOnly ? (
                            <span>
                              {MIX_TYPE_OPTIONS.find((o) => o.value === row.mixType)?.label ??
                                row.mixType}
                            </span>
                          ) : (
                            <SelectListbox
                              value={row.mixType}
                              options={MIX_TYPE_OPTIONS}
                              onChange={(v) => {
                                updateSimplifiedRow(idx, "mixType", v);
                                syncSimplifiedRow({ ...row, mixType: v });
                              }}
                              aria-label="Mix type"
                            />
                          )}
                        </td>
                        <td className={cellCls}>
                          {readOnly ? (
                            <span>{formatDisplayNumber(row.strengthMpa)} MPa</span>
                          ) : (
                            <SelectListbox
                              value={row.strengthMpa}
                              options={STRENGTH_OPTIONS}
                              onChange={(v) => {
                                updateSimplifiedRow(idx, "strengthMpa", v);
                                syncSimplifiedRow({ ...row, strengthMpa: v });
                              }}
                              aria-label="Strength"
                            />
                          )}
                        </td>
                        <td className={cellCls}>
                          {readOnly ? (
                            <span>{row.scmPct !== null ? `${formatDisplayNumber(row.scmPct)}%` : "-"}</span>
                          ) : (
                            <NumericInput
                              value={row.scmPct}
                              allowDecimal
                              onChange={(v) =>
                                updateSimplifiedRow(
                                  idx,
                                  "scmPct",
                                  typeof v === "number"
                                    ? Math.min(100, Math.max(0, v))
                                    : null
                                )
                              }
                              onBlur={() => syncSimplifiedRow(row)}
                              ariaLabel="SCM content %"
                            />
                          )}
                        </td>
                        <td className={cellCls}>
                          {readOnly ? (
                            <span>{formatDisplayNumber(row.volumeM3)}</span>
                          ) : (
                            <NumericInput
                              value={row.volumeM3}
                              allowDecimal
                              onChange={(v) =>
                                updateSimplifiedRow(
                                  idx,
                                  "volumeM3",
                                  typeof v === "number" ? v : null
                                )
                              }
                              onBlur={() => syncSimplifiedRow(row)}
                              ariaLabel="Volume m3"
                            />
                          )}
                        </td>
                        <td className={cellCls}>
                          <span className="text-text-faint">{fmtEmissions(emissions)}</span>
                        </td>
                        <td className={cellCls}>
                          {readOnly ? (
                            <span>{row.notes || "-"}</span>
                          ) : (
                            <input
                              type="text"
                              value={row.notes}
                              onChange={(e) =>
                                updateSimplifiedRow(idx, "notes", e.target.value)
                              }
                              onBlur={() => syncSimplifiedRow(row)}
                              className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                              aria-label="Notes"
                            />
                          )}
                        </td>
                        <td className="whitespace-nowrap px-2 py-3 w-20">
                          {!readOnly && (
                            <button
                              type="button"
                              title="Delete row"
                              onClick={() => deleteSimplifiedRow(row.id)}
                              className="inline-flex items-center cursor-pointer justify-center h-8 w-8 rounded hover:bg-neutral-95 text-text-faint hover:text-red-600"
                            >
                              <span className="material-symbols-rounded text-[20px]">delete</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}

                  {simplifiedDraft && (
                    <tr className="bg-neutral-98">
                      <td className={cellCls}>
                        <SelectListbox
                          value={simplifiedDraft.mixType}
                          options={MIX_TYPE_OPTIONS}
                          onChange={(v) => updateSimplifiedDraft("mixType", v)}
                          aria-label="Mix type"
                        />
                      </td>
                      <td className={cellCls}>
                        <SelectListbox
                          value={simplifiedDraft.strengthMpa}
                          options={STRENGTH_OPTIONS}
                          onChange={(v) => updateSimplifiedDraft("strengthMpa", v)}
                          aria-label="Strength"
                        />
                      </td>
                      <td className={cellCls}>
                        <NumericInput
                          value={simplifiedDraft.scmPct}
                          allowDecimal
                          onChange={(v) =>
                            updateSimplifiedDraft(
                              "scmPct",
                              typeof v === "number" ? Math.min(100, Math.max(0, v)) : null
                            )
                          }
                          ariaLabel="SCM content %"
                        />
                      </td>
                      <td className={cellCls}>
                        <NumericInput
                          value={simplifiedDraft.volumeM3}
                          allowDecimal
                          onChange={(v) =>
                            updateSimplifiedDraft("volumeM3", typeof v === "number" ? v : null)
                          }
                          ariaLabel="Volume m3"
                        />
                      </td>
                      <td className={cellCls}>
                        <span className="text-text-faint">-</span>
                      </td>
                      <td className={cellCls}>
                        <input
                          type="text"
                          value={simplifiedDraft.notes}
                          onChange={(e) => updateSimplifiedDraft("notes", e.target.value)}
                          className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                          aria-label="Notes"
                        />
                      </td>
                      <td className="whitespace-nowrap px-2 py-3 w-20">
                        <div className="flex items-center gap-1 justify-end">
                          <button
                            type="button"
                            title="Save"
                            onClick={() => void saveSimplifiedDraft()}
                            className="inline-flex items-center cursor-pointer justify-center h-8 w-8 rounded text-primary hover:bg-neutral-95"
                          >
                            <span className="material-symbols-rounded text-success">check</span>
                          </button>
                          <button
                            type="button"
                            title="Cancel"
                            onClick={cancelSimplifiedDraft}
                            className="inline-flex items-center cursor-pointer justify-center h-8 w-8 rounded text-primary hover:bg-neutral-95"
                          >
                            <span className="material-symbols-rounded text-[20px]">close</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === "Detailed" && (
            <div>
              <div className="flex border-b border-neutral-90 mb-4">
                {DETAILED_SUBTABS.map((sub) => (
                  <button
                    key={sub}
                    type="button"
                    onClick={() => setDetailedSubTab(sub)}
                    className={[
                      "px-3 py-1.5 text-xs cursor-pointer font-medium focus:outline-none",
                      detailedSubTab === sub
                        ? "border-b-2 border-primary text-primary"
                        : "text-text-faint hover:text-text-base",
                    ].join(" ")}
                  >
                    {sub}
                  </button>
                ))}
              </div>

              {detailedSubTab === "Mix Design" && (
                <div>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mt-4 mb-5 gap-4">
                    {!readOnly && (
                      <div className="flex flex-wrap gap-6 text-primary text-sm">
                        <button type="button" className="flex items-center gap-1 hover:bg-neutral-90 px-0.5">
                          <img src={Download} alt="" className="h-5 w-5" />
                          <span className="font-medium">{mixRows.length ? "Export to Excel" : "Download blank template"}</span>
                        </button>
                        <button type="button" className="flex items-center gap-1 hover:bg-neutral-90 px-0.5">
                          <img src={UploadFile} alt="" className="h-5 w-5" />
                          <span className="font-medium">Upload file</span>
                        </button>
                        <button type="button" onClick={() => void addMixRow()} className="flex items-center gap-1 cursor-pointer hover:bg-neutral-90 px-0.5">
                          <img src={AddIcon} alt="" className="h-5 w-5" />
                          <span className="font-medium">Add row</span>
                        </button>
                      </div>
                    )}
                  </div>
                  <table className="border border-neutral-90 w-full text-sm">
                    <thead>
                      <tr>
                        <th className={`${headCls} w-8`} />
                        <th className={headCls}>Mix ID</th>
                        <th className={headCls}>Mix Type</th>
                        <th className={headCls}>Strength (MPa)</th>
                        <th className={headCls}>Volume (m&#179;)</th>
                        <th className={headCls}>Carbon Intensity A1-A3 (kgCO&#8322;e/m&#179;)</th>
                        <th className={headCls}>Emissions (tCO&#8322;e)</th>
                        <th className={headCls}>Notes</th>
                        {!readOnly && <th className={`${headCls} w-12`} />}
                      </tr>
                    </thead>
                    <tbody>
                      {mixRows.length === 0 && (
                        <tr>
                          <td colSpan={readOnly ? 8 : 9} className="px-4 py-10 text-center text-neutral-90">
                            <div className="text-base font-medium">No data yet</div>
                            <div className="text-sm">Get started by adding data manually or uploading a file</div>
                          </td>
                        </tr>
                      )}
                      {mixRows.map((row) => {
                        const ci = getCarbonIntensity(row.id);
                        const emissions = getMixEmissions(row);
                        const mats = materialsMap[row.id] ?? [];
                        return (
                          <React.Fragment key={row.id}>
                            <tr>
                              <td className={`${cellCls} text-center`}>
                                <button
                                  type="button"
                                  onClick={() => toggleMixExpanded(row.id)}
                                  className="inline-flex items-center justify-center cursor-pointer focus:outline-none"
                                  aria-label={
                                    row.expanded ? "Collapse materials" : "Expand materials"
                                  }
                                >
                                  <span className="material-symbols-rounded text-base text-text-faint">
                                    {row.expanded ? "expand_less" : "expand_more"}
                                  </span>
                                </button>
                              </td>
                              <td className={cellCls}>
                                {readOnly ? (
                                  <span>{row.mixId || "-"}</span>
                                ) : (
                                  <input
                                    type="text"
                                    value={row.mixId}
                                    onChange={(e) =>
                                      updateMixRow(row.id, "mixId", e.target.value)
                                    }
                                    onBlur={() => syncMixRow(row)}
                                    className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                                    aria-label="Mix ID"
                                  />
                                )}
                              </td>
                              <td className={cellCls}>
                                {readOnly ? (
                                  <span>
                                    {MIX_TYPE_OPTIONS.find((o) => o.value === row.mixType)
                                      ?.label ?? row.mixType}
                                  </span>
                                ) : (
                                  <SelectListbox
                                    value={row.mixType}
                                    options={MIX_TYPE_OPTIONS}
                                    onChange={(v) => {
                                      updateMixRow(row.id, "mixType", v);
                                      syncMixRow({ ...row, mixType: v });
                                    }}
                                    aria-label="Mix type"
                                  />
                                )}
                              </td>
                              <td className={cellCls}>
                                {readOnly ? (
                                  <span>{formatDisplayNumber(row.strengthMpa)} MPa</span>
                                ) : (
                                  <SelectListbox
                                    value={row.strengthMpa}
                                    options={STRENGTH_OPTIONS}
                                    onChange={(v) => {
                                      updateMixRow(row.id, "strengthMpa", v);
                                      syncMixRow({ ...row, strengthMpa: v });
                                    }}
                                    aria-label="Strength"
                                  />
                                )}
                              </td>
                              <td className={cellCls}>
                                {readOnly ? (
                                  <span>{formatDisplayNumber(row.volumeM3)}</span>
                                ) : (
                                  <NumericInput
                                    value={row.volumeM3}
                                    allowDecimal
                                    onChange={(v) =>
                                      updateMixRow(
                                        row.id,
                                        "volumeM3",
                                        typeof v === "number" ? v : null
                                      )
                                    }
                                    onBlur={() => syncMixRow(row)}
                                    ariaLabel="Volume m3"
                                  />
                                )}
                              </td>
                              <td className={cellCls}>
                                <span className="text-text-faint">
                                  {formatDisplayNumber(ci, { decimalsBelowThreshold: 4, threshold: Number.MAX_SAFE_INTEGER })}
                                </span>
                              </td>
                              <td className={cellCls}>
                                <span className="text-text-faint">{fmtEmissions(emissions)}</span>
                              </td>
                              <td className={cellCls}>
                                {readOnly ? (
                                  <span>{row.notes || "-"}</span>
                                ) : (
                                  <input
                                    type="text"
                                    value={row.notes}
                                    onChange={(e) =>
                                      updateMixRow(row.id, "notes", e.target.value)
                                    }
                                    onBlur={() => syncMixRow(row)}
                                    className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                                    aria-label="Notes"
                                  />
                                )}
                              </td>
                              {!readOnly && (
                                <td className="whitespace-nowrap px-2 py-3 w-12">
                                  <button
                                    type="button"
                                    title="Delete mix"
                                    onClick={() => void deleteMixRow(row.id)}
                                    className="inline-flex items-center justify-center h-8 w-8 cursor-pointer rounded hover:bg-neutral-95 text-text-faint hover:text-red-600"
                                  >
                                    <span className="material-symbols-rounded text-[20px]">delete</span>
                                  </button>
                                </td>
                              )}
                            </tr>

                            {row.expanded && (
                              <tr>
                                <td
                                  colSpan={readOnly ? 8 : 9}
                                  className="px-8 pb-4 pt-1 border-b border-neutral-90 bg-neutral-98"
                                >
                                  <div className="text-xs font-semibold text-text-faint uppercase mb-2">
                                    Mix components &#8212; {row.mixId || "Untitled mix"}
                                  </div>
                                  <table className="w-full text-sm border border-neutral-90">
                                    <thead>
                                      <tr>
                                        <th className={headCls}>Material name</th>
                                        <th className={headCls}>Quantity (kg/m&#179;)</th>
                                        <th className={headCls}>
                                          Carbon factor (kgCO&#8322;e/kg)
                                        </th>
                                        <th className={headCls}>
                                          Emissions (kgCO&#8322;e/m&#179;)
                                        </th>
                                        {!readOnly && <th className={`${headCls} w-10`} />}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {mats.length === 0 && (
                                        <tr>
                                          <td
                                            colSpan={readOnly ? 4 : 5}
                                            className={`${cellCls} text-center text-text-faint py-4`}
                                          >
                                            No materials yet
                                          </td>
                                        </tr>
                                      )}
                                      {mats.map((mat) => {
                                        const matEmissions =
                                          mat.quantityKgM3 !== null &&
                                          mat.carbonFactor !== null
                                            ? mat.quantityKgM3 * mat.carbonFactor
                                            : null;
                                        return (
                                          <tr key={mat.id}>
                                            <td className={cellCls}>
                                              {readOnly ? (
                                                <span>{mat.materialName || "-"}</span>
                                              ) : (
                                                <input
                                                  type="text"
                                                  value={mat.materialName}
                                                  onChange={(e) =>
                                                    updateMaterial(
                                                      row.id,
                                                      mat.id,
                                                      "materialName",
                                                      e.target.value
                                                    )
                                                  }
                                                  onBlur={() => syncMaterial(mat)}
                                                  className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                                                  aria-label="Material name"
                                                />
                                              )}
                                            </td>
                                            <td className={cellCls}>
                                              {readOnly ? (
                                                <span>{formatDisplayNumber(mat.quantityKgM3)}</span>
                                              ) : (
                                                <NumericInput
                                                  value={mat.quantityKgM3}
                                                  allowDecimal
                                                  onChange={(v) =>
                                                    updateMaterial(
                                                      row.id,
                                                      mat.id,
                                                      "quantityKgM3",
                                                      typeof v === "number" ? v : null
                                                    )
                                                  }
                                                  onBlur={() => syncMaterial(mat)}
                                                  ariaLabel="Quantity kg per m3"
                                                />
                                              )}
                                            </td>
                                            <td className={cellCls}>
                                              {readOnly ? (
                                                <span>{formatDisplayNumber(mat.carbonFactor, { decimalsBelowThreshold: 4, threshold: Number.MAX_SAFE_INTEGER })}</span>
                                              ) : (
                                                <NumericInput
                                                  value={mat.carbonFactor}
                                                  allowDecimal
                                                  onChange={(v) =>
                                                    updateMaterial(
                                                      row.id,
                                                      mat.id,
                                                      "carbonFactor",
                                                      typeof v === "number" ? v : null
                                                    )
                                                  }
                                                  onBlur={() => syncMaterial(mat)}
                                                  ariaLabel="Carbon factor"
                                                />
                                              )}
                                            </td>
                                            <td className={cellCls}>
                                              <span className="text-text-faint">
                                                {matEmissions !== null
                                                  ? formatDisplayNumber(matEmissions, { decimalsBelowThreshold: 4, threshold: Number.MAX_SAFE_INTEGER })
                                                  : "-"}
                                              </span>
                                            </td>
                                            {!readOnly && (
                                              <td className="px-2 py-2 w-10">
                                                <button
                                                  type="button"
                                                  title="Delete material"
                                                  onClick={() =>
                                                    void deleteMaterial(row.id, mat.id)
                                                  }
                                                  className="inline-flex items-center cursor-pointer justify-center h-7 w-7 rounded hover:bg-neutral-90 text-text-faint hover:text-red-600"
                                                >
                                                  <span className="material-symbols-rounded text-[18px]">
                                                    delete
                                                  </span>
                                                </button>
                                              </td>
                                            )}
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>

                                  {!readOnly && (
                                    <button
                                      type="button"
                                      onClick={() => void addMaterial(row.id)}
                                      className="mt-2 text-sm text-primary flex cursor-pointer items-center gap-1 hover:underline"
                                    >
                                      <span className="material-symbols-rounded text-base">
                                        add
                                      </span>
                                      Add material
                                    </button>
                                  )}
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </tbody>
                  </table>

                </div>
              )}

              {detailedSubTab === "EPD / PCF" && (
                <div>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mt-4 mb-5 gap-4">
                    {!readOnly && (
                      <div className="flex flex-wrap gap-6 text-primary text-sm">
                        <button type="button" className="flex items-center gap-1 hover:bg-neutral-90 px-0.5">
                          <img src={Download} alt="" className="h-5 w-5" />
                          <span className="font-medium">{epdRows.length ? "Export to Excel" : "Download blank template"}</span>
                        </button>
                        <button type="button" className="flex items-center gap-1 hover:bg-neutral-90 px-0.5">
                          <img src={UploadFile} alt="" className="h-5 w-5" />
                          <span className="font-medium">Upload file</span>
                        </button>
                        <button type="button" onClick={() => void addEpdRow()} className="flex items-center gap-1 cursor-pointer hover:bg-neutral-90 px-0.5">
                          <img src={AddIcon} alt="" className="h-5 w-5" />
                          <span className="font-medium">Add row</span>
                        </button>
                      </div>
                    )}
                  </div>
                  <table className="border border-neutral-90 w-full text-sm">
                    <thead>
                      <tr>
                        <th className={headCls}>Mix ID</th>
                        <th className={headCls}>GWP Total A1-A3 (kgCO&#8322;e/m&#179;)</th>
                        <th className={headCls}>Volume (m&#179;)</th>
                        <th className={headCls}>Emissions (tCO&#8322;e)</th>
                        <th className={headCls}>Notes</th>
                        {!readOnly && <th className={`${headCls} w-12`} />}
                      </tr>
                    </thead>
                    <tbody>
                      {epdRows.length === 0 && (
                        <tr>
                          <td colSpan={readOnly ? 5 : 6} className="px-4 py-10 text-center text-neutral-90">
                            <div className="text-base font-medium">No data yet</div>
                            <div className="text-sm">Get started by adding data manually or uploading a file</div>
                          </td>
                        </tr>
                      )}
                      {epdRows.map((row) => {
                        const emissions = getEpdEmissions(row);
                        return (
                          <tr key={row.id}>
                            <td className={cellCls}>
                              {readOnly ? (
                                <span>{row.mixId || "-"}</span>
                              ) : (
                                <input
                                  type="text"
                                  value={row.mixId}
                                  onChange={(e) =>
                                    updateEpdRow(row.id, "mixId", e.target.value)
                                  }
                                  onBlur={() => syncEpdRow(row)}
                                  className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                                  aria-label="Mix ID"
                                />
                              )}
                            </td>
                            <td className={cellCls}>
                              {readOnly ? (
                                <span>{formatDisplayNumber(row.gwpA1A3, { decimalsBelowThreshold: 4, threshold: Number.MAX_SAFE_INTEGER })}</span>
                              ) : (
                                <NumericInput
                                  value={row.gwpA1A3}
                                  allowDecimal
                                  onChange={(v) =>
                                    updateEpdRow(
                                      row.id,
                                      "gwpA1A3",
                                      typeof v === "number" ? v : null
                                    )
                                  }
                                  onBlur={() => syncEpdRow(row)}
                                  ariaLabel="GWP A1-A3"
                                />
                              )}
                            </td>
                            <td className={cellCls}>
                              {readOnly ? (
                                <span>{formatDisplayNumber(row.volumeM3)}</span>
                              ) : (
                                <NumericInput
                                  value={row.volumeM3}
                                  allowDecimal
                                  onChange={(v) =>
                                    updateEpdRow(
                                      row.id,
                                      "volumeM3",
                                      typeof v === "number" ? v : null
                                    )
                                  }
                                  onBlur={() => syncEpdRow(row)}
                                  ariaLabel="Volume m3"
                                />
                              )}
                            </td>
                            <td className={cellCls}>
                              <span className="text-text-faint">{fmtEmissions(emissions)}</span>
                            </td>
                            <td className={cellCls}>
                              {readOnly ? (
                                <span>{row.notes || "-"}</span>
                              ) : (
                                <input
                                  type="text"
                                  value={row.notes}
                                  onChange={(e) =>
                                    updateEpdRow(row.id, "notes", e.target.value)
                                  }
                                  onBlur={() => syncEpdRow(row)}
                                  className="w-full border border-neutral-90 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                                  aria-label="Notes"
                                />
                              )}
                            </td>
                            {!readOnly && (
                              <td className="whitespace-nowrap px-2 py-3 w-12">
                                <button
                                  type="button"
                                  title="Delete row"
                                  onClick={() => void deleteEpdRow(row.id)}
                                  className="inline-flex items-center justify-center cursor-pointer h-8 w-8 rounded hover:bg-neutral-95 text-text-faint hover:text-red-600"
                                >
                                  <span className="material-symbols-rounded text-[20px]">delete</span>
                                </button>
                              </td>
                            )}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConcreteRegister;
