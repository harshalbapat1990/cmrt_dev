import React, { useState } from "react";
import { formatDisplayNumber } from "@/utils/utils";
import { SelectListbox } from "@/components/common/Select";
import { NumericInput } from "@/components/common/NumericInput";
import Download from "@/assets/icons/download.svg";
import UploadFile from "@/assets/icons/upload_file.svg";
import AddIcon from "@/assets/icons/add.svg";
import { useConcreteRegisterData } from "./hooks/useConcreteRegisterData";
import { useConcreteRegisterActions } from "./hooks/useConcreteRegisterActions";
import { ConcreteEpdPcfTable } from "./components/ConcreteEpdPcfTable";
import {
  CONCRETE_STRENGTHS,
  MIX_TYPE_OPTIONS,
} from "./concreteRegisterTypes";

export { CONCRETE_STRENGTHS, MIX_TYPE_OPTIONS } from "./concreteRegisterTypes";

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

export type { EpdRow, MaterialRow, MixRow, SimplifiedRow } from "./concreteRegisterTypes";

function fmtEmissions(val: number | null): string {
  return formatDisplayNumber(val, { decimalsBelowThreshold: 4, threshold: Number.MAX_SAFE_INTEGER });
}

const ConcreteRegister: React.FC<ConcreteRegisterProps> = ({ projectId, readOnly = false }) => {
  const [open, setOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<RegisterTab>("Simplified");
  const [detailedSubTab, setDetailedSubTab] = useState<DetailedSubTab>("Mix Design");
  const register = useConcreteRegisterData(projectId);
  const actions = useConcreteRegisterActions({ projectId, ...register });
  const {
    loading, simplifiedRows, mixRows, materialsMap, epdRows,
  } = register;
  const {
    simplifiedDraft, addSimplifiedRow, updateSimplifiedDraft,
    saveSimplifiedDraft, cancelSimplifiedDraft, updateSimplifiedRow,
    syncSimplifiedRow, deleteSimplifiedRow, getSimplifiedEmissions,
    addMixRow, updateMixRow, syncMixRow, deleteMixRow, toggleMixExpanded,
    addMaterial, updateMaterial, syncMaterial, deleteMaterial, getCarbonIntensity,
    getMixEmissions,
  } = actions;
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

              {detailedSubTab === "EPD / PCF" && <ConcreteEpdPcfTable rows={epdRows} readOnly={readOnly} actions={actions} />}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConcreteRegister;
