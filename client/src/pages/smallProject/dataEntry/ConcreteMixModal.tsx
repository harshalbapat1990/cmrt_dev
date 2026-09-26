import { useState, useEffect, useRef } from "react";
import { formatDisplayNumber } from "@/utils/utils";
import { SelectListbox } from "@/components/common/Select";
import { NumericInput } from "@/components/common/NumericInput";
import ActivityDataService from "@/services/ActivityData.service";
import EmissionCalculationsService from "@/services/EmissionCalculations.service";
import { apiRowToUiRow } from "./rowTransforms";

const MIX_TYPE_OPTIONS = [
    { label: "Ready-mix", value: "Ready-mix" },
    { label: "Precast", value: "Precast" },
];

const STRENGTH_OPTIONS = [
    { label: "5 MPa", value: "5" },
    { label: "10 MPa", value: "10" },
    { label: "15 MPa", value: "15" },
    { label: "20 MPa", value: "20" },
    { label: "25 MPa", value: "25" },
    { label: "32 MPa", value: "32" },
    { label: "40 MPa", value: "40" },
    { label: "50 MPa", value: "50" },
    { label: "65 MPa", value: "65" },
    { label: "80 MPa", value: "80" },
    { label: "100 MPa", value: "100" },
];

const DEFAULT_MATERIALS = [
    "General purpose cement",
    "Fly ash",
    "GGBF slag",
    "Silica Fume",
    "Fine Aggregates",
    "Coarse Aggregates",
    "Recycled Aggregates",
    "Manufactured sand",
    "Mains Water",
    "Onsite Recycled / Captured Water",
    "Admixture",
];

interface MaterialDraft {
    id?: string; // existing material ID when editing
    materialName: string;
    quantityKgM3: number | null;
    carbonFactor: number | null;
}

interface Props {
    projectId: string;
    stageInstanceId: string;
    optionId: string | null;
    modalType: "mix_design" | "epd_pcf";
    onClose: () => void;
    onCreated: (row: any) => void;
    /** When provided, the modal opens in edit mode with prefilled values */
    editMix?: any;
    calculateConcreteDetailed?: (row: any) => Promise<Partial<any> | null>;
}

const LABEL_CLS = "block text-xs text-text-faint mb-1 font-medium";
const INPUT_BORDER = "border border-border-input rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-primary";

export default function ConcreteMixModal({ projectId, stageInstanceId, optionId, modalType, onClose, onCreated, editMix, calculateConcreteDetailed }: Props) {
    const isEditing = !!editMix;
    const isEpd = modalType === "epd_pcf";

    // editMix is a UI row from apiRowToUiRow (extra_fields spread to top level)
    // strength is stored as "25MPa", strip "MPa" to get the option value
    const [mixIdLabel, setMixIdLabel] = useState(editMix?.mixId ?? "");
    const [mixType, setMixType] = useState(
        editMix?.mixType ?? MIX_TYPE_OPTIONS[0].value
    );
    const [strength, setStrength] = useState(
        editMix?.strength != null
            ? String(editMix.strength).replace(/MPa$/i, "")
            : STRENGTH_OPTIONS[3].value
    );
    const [gwpA1A3, setGwpA1A3] = useState<number | null>(editMix?.gwpA1A3 ?? null);
    const [volumeM3, setVolumeM3] = useState<number | null>(
        // volume is stored in activity_data.quantity
        editMix?.quantity != null ? Number(editMix.quantity) : null
    );
    const [materials, setMaterials] = useState<MaterialDraft[]>(() => {
        // materials stored as JSON array in extra_fields.materials
        const existing = new Map(
            ((editMix?.materials ?? []) as MaterialDraft[]).map((m) => [m.materialName, m])
        );
        return DEFAULT_MATERIALS.map((name) => {
            const found = existing.get(name);
            return {
                materialName: name,
                quantityKgM3: found?.quantityKgM3 ?? null,
                carbonFactor: found?.carbonFactor ?? null,
            };
        });
    });
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [liveGwpKgCo2eM3, setLiveGwpKgCo2eM3] = useState<number | null>(null);
    const calcTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        if (isEpd) return;
        const hasMaterial = materials.some((m) => m.quantityKgM3 !== null);
        if (!hasMaterial) {
            setLiveGwpKgCo2eM3(null);
            return;
        }
        if (calcTimerRef.current) clearTimeout(calcTimerRef.current);
        calcTimerRef.current = setTimeout(async () => {
            try {
                const payload = {
                    project_id: projectId,
                    mix_id_label: "_preview",
                    mix_type: mixType,
                    strength_mpa: Number(strength),
                    volume_m3: 1,
                    materials: materials
                        .filter((m) => m.quantityKgM3 !== null)
                        .map((m) => ({
                            material_name: m.materialName,
                            quantity_kg_m3: m.quantityKgM3,
                        })),
                };
                const res = await EmissionCalculationsService.concreteRegNewMixCalculations(payload);
                setLiveGwpKgCo2eM3(Number(res.gwp_a1a3_kgco2e_m3));
            } catch {
                // silently ignore preview calculation errors
            }
        }, 500);
        return () => {
            if (calcTimerRef.current) clearTimeout(calcTimerRef.current);
        };
    }, [materials, mixType, strength, projectId, isEpd]);

    const updateMaterial = (idx: number, key: keyof MaterialDraft, value: any) => {
        setMaterials((prev) => prev.map((m, i) => (i === idx ? { ...m, [key]: value } : m)));
    };

    const getNumericEmission = (patch: Partial<any> | null): number | null => {
        const raw = patch?.total_emissions_tco2e ?? patch?.emissions_tco2e;
        if (
            raw === "-" ||
            raw === "" ||
            raw == null ||
            Number.isNaN(Number(raw))
        ) {
            return null;
        }
        return Number(raw);
    };

    const handleSave = async () => {
        if (!mixIdLabel.trim()) {
            setError("Mix ID is required.");
            return;
        }
        const materialsForCalculation = materials
            .filter((m) => m.quantityKgM3 !== null && m.quantityKgM3 !== undefined)
            .map((m) => ({
                materialName: m.materialName,
                quantityKgM3: Number(m.quantityKgM3),
                carbonFactor: m.carbonFactor,
            }));

        if (!isEpd && materialsForCalculation.length === 0) {
            setError("Please enter at least one material quantity.");
            return;
        }

        if (volumeM3 == null) {
            setError("Volume is required.");
            return;
        }

        if (isEpd && gwpA1A3 == null) {
            setError("GWP Total is required.");
            return;
        }

        if (!calculateConcreteDetailed) {
            setError("Calculation function is unavailable.");
            return;
        }

        setSaving(true);
        setError(null);
        try {
            const calculationRow = {
                method: modalType,
                mixId: mixIdLabel.trim(),
                mixType,
                strength,
                volume: volumeM3,
                gwpA1A3,
                materials: materialsForCalculation,
            };
            const calcPatch = await calculateConcreteDetailed(calculationRow);
            if ((calcPatch as any)?._calculation_error) {
                setError((calcPatch as any)._calculation_error);
                return;
            }
            const calculatedEmissions = getNumericEmission(calcPatch);
            if (calculatedEmissions == null) {
                setError("Unable to calculate emissions. Please check the mix details and material quantities.");
                return;
            }

            const extra_fields: any = {
                method: modalType,
                mixId: mixIdLabel.trim(),
                mixType,
                strength: `${strength}MPa`,
                volume: volumeM3,
                gwpA1A3: isEpd ? gwpA1A3 : null,
                notes: editMix?.notes ?? "",
                emissions_tco2e: calculatedEmissions,
                total_emissions_tco2e: calculatedEmissions,
            };
            if (!isEpd) {
                extra_fields.materials = materials
                    .filter((m) => m.quantityKgM3 !== null || m.carbonFactor !== null)
                    .map((m) => ({
                        materialName: m.materialName,
                        quantityKgM3: m.quantityKgM3,
                        carbonFactor: m.carbonFactor,
                    }));
            }

            let saved: any;
            if (isEditing && editMix) {
                saved = await ActivityDataService.updateRow(editMix.id, {
                    quantity: volumeM3,
                    emissions_tco2e: calculatedEmissions,
                    extra_fields,
                });
            } else {
                saved = await ActivityDataService.createRow({
                    project_id: projectId,
                    project_stage_instance_id: stageInstanceId,
                    project_option_id: optionId ?? null,
                    metric_id: null,
                    quantity: volumeM3,
                    unit_id: null,
                    emissions_tco2e: calculatedEmissions,
                    ui_table_key: "concreteRegDetailed",
                    extra_fields,
                });
            }

            onCreated(apiRowToUiRow(saved));
        } catch (e) {
            console.error("Failed to save concrete mix:", e);
            setError("Failed to save. Please try again.");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div
                className="bg-white rounded-lg shadow-xl w-full mx-4 flex flex-col"
                style={{ maxWidth: isEpd ? 520 : 720, maxHeight: "90vh" }}
            >
                {/* Header */}
                <div className="px-8 pt-8 pb-4 border-b border-neutral-90 flex-shrink-0">
                    <h2 className="text-2xl text-text-dark font-light mb-1">Concrete mix register</h2>
                    <div className="text-sm text-text-faint">
                        {isEditing
                            ? (isEpd ? "Edit mix with EPD/PCF" : "Edit mix with mix design")
                            : (isEpd ? "New mix with EPD/PCF" : "New mix with mix design")}
                    </div>
                </div>

                {/* Body */}
                <div className="px-8 py-6 overflow-y-auto flex-1">
                    {/* Common fields */}
                    <div className={`grid gap-4 mb-6 ${isEpd ? "grid-cols-2" : "grid-cols-3"}`}>
                        <div>
                            <label className={LABEL_CLS}>Mix ID <span className="text-red-500">*</span></label>
                            <input
                                className={INPUT_BORDER}
                                value={mixIdLabel}
                                onChange={(e) => setMixIdLabel(e.target.value)}
                                placeholder="e.g. MIX-001"
                            />
                        </div>
                        <div>
                            <label className={LABEL_CLS}>Mix type</label>
                            <SelectListbox
                                value={mixType}
                                options={MIX_TYPE_OPTIONS}
                                onChange={(v: string) => setMixType(v)}
                            />
                        </div>
                        <div>
                            <label className={LABEL_CLS}>Strength (MPa)</label>
                            <SelectListbox
                                value={strength}
                                options={STRENGTH_OPTIONS}
                                onChange={(v: string) => setStrength(v)}
                            />
                        </div>
                        {isEpd && (
                            <div>
                                <label className={LABEL_CLS}>GWP Total (A1-A3) (kgCO₂e/m³)</label>
                                <NumericInput
                                    value={gwpA1A3}
                                    onChange={(v) => setGwpA1A3(v !== null ? Number(v) : null)}
                                    allowDecimal
                                    ariaLabel="GWP A1-A3"
                                />
                            </div>
                        )}
                        {isEpd && (
                            <div>
                                <label className={LABEL_CLS}>Volume (m³)</label>
                                <NumericInput
                                    value={volumeM3}
                                    onChange={(v) => setVolumeM3(v !== null ? Number(v) : null)}
                                    allowDecimal
                                    ariaLabel="Volume m3"
                                />
                            </div>
                        )}
                    </div>

                    {/* Mix design materials table */}
                    {!isEpd && (
                        <>
                            <div className="border border-neutral-90 rounded overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead className="bg-neutral-95 text-text-faint text-xs">
                                        <tr>
                                            <th className="px-3 py-2 text-left font-medium">Component</th>
                                            <th className="px-3 py-2 text-right font-medium">Mix content (kg/m³)</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-neutral-90">
                                        {materials.map((mat, idx) => (
                                            <tr key={mat.materialName}>
                                                <td className="px-3 py-2 text-text-base">{mat.materialName}</td>
                                                <td className="px-3 py-2">
                                                    <NumericInput
                                                        value={mat.quantityKgM3}
                                                        onChange={(v) => updateMaterial(idx, "quantityKgM3", v !== null ? Number(v) : null)}
                                                        allowDecimal
                                                        ariaLabel={`${mat.materialName} kg/m3`}
                                                        className="text-right"
                                                    />
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                    <tfoot className="bg-neutral-95 border-t border-neutral-90">
                                        <tr>
                                            <td className="px-3 py-2 text-xs text-text-faint font-bold">
                                                Carbon intensity (A1 - A3) (kgCO₂e/m³)*
                                            </td>
                                            <td className="px-3 py-2 text-sm text-right font-medium text-text-dark">
                                                {formatDisplayNumber(liveGwpKgCo2eM3)}
                                            </td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>

                            {/* Volume for mix_design */}
                            <div className="mt-4 max-w-xs">
                                <label className={LABEL_CLS}>Volume (m³)</label>
                                <NumericInput
                                    value={volumeM3}
                                    onChange={(v) => setVolumeM3(v !== null ? Number(v) : null)}
                                    allowDecimal
                                    ariaLabel="Volume m3"
                                />
                            </div>
                        </>
                    )}

                    {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
                </div>

                {/* Footer */}
                <div className="px-8 py-5 border-t border-neutral-90 flex justify-end gap-3 flex-shrink-0">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={saving}
                        className="px-5 py-2 text-sm cursor-pointer font-medium border border-border rounded text-text-base hover:bg-neutral-95 transition-colors disabled:opacity-40"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onClick={handleSave}
                        disabled={saving}
                        className="px-5 py-2 text-sm font-medium cursor-pointer rounded bg-primary text-white hover:opacity-90 transition-opacity disabled:opacity-40"
                    >
                        {saving ? "Saving…" : isEditing ? "Update" : "Add"}
                    </button>
                </div>
            </div>
        </div>
    );
}
