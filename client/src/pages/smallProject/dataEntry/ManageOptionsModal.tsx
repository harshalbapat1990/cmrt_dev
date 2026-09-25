import { useState } from "react";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import ProjectOptionsService from "@/services/ProjectOptions.service";
import DeleteOptionModal from "./DeleteOptionModal";

interface Props {
    open: boolean;
    onClose: () => void;
    activeStage: string;
    projectId: string;
    stageInstanceId: string;
    reportNumber: number;
    options: ProjectOption[];
    onOptionsChange: () => Promise<void>;
}

export default function ManageOptionsModal({
    open,
    onClose,
    activeStage,
    projectId,
    stageInstanceId,
    reportNumber,
    options,
    onOptionsChange,
}: Props) {
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editLabel, setEditLabel] = useState("");
    const [deleteTarget, setDeleteTarget] = useState<ProjectOption | null>(null);
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    if (!open) return null;

    const nextOptionNumber = options.length + 1;

    const handleAddOption = async () => {
        setLoading(true);
        try {
            await ProjectOptionsService.createSubOption(
                projectId,
                stageInstanceId,
                reportNumber,
                `${activeStage} - option ${nextOptionNumber}`,
            );
            await onOptionsChange();
        } catch (e) {
            console.error("Failed to add option:", e);
        } finally {
            setLoading(false);
        }
    };

    const handleEditConfirm = async (id: string) => {
        if (!editLabel.trim()) return;
        setLoading(true);
        try {
            await ProjectOptionsService.renameOption(id, editLabel.trim());
            await onOptionsChange();
        } catch (e) {
            console.error("Failed to rename option:", e);
        } finally {
            setEditingId(null);
            setEditLabel("");
            setLoading(false);
        }
    };

    const handleSetDefault = async (id: string) => {
        setLoading(true);
        try {
            await ProjectOptionsService.setDefaultOption(id);
            await onOptionsChange();
        } catch (e) {
            console.error("Failed to set default:", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                <div className="bg-white rounded-lg shadow-xl p-8 max-w-lg w-full mx-4">
                    <div className="flex items-start justify-between mb-6">
                        <h2 className="text-2xl text-text-dark">Manage options</h2>
                    </div>
                    <p className="text-base text-text-base mb-6">
                        Define your options below. You can only set one option as your base case.
                    </p>

                    <div className="flex justify-end mb-2">
                        <button
                            className="flex items-center gap-1 text-sm font-medium text-primary cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-40"
                            onClick={handleAddOption}
                            disabled={loading}
                        >
                            <span className="material-symbols-rounded text-base">add</span>
                            Add option
                        </button>
                    </div>

                    <div className="flex flex-col gap-2 max-h-72 overflow-y-auto mb-12">
                        {options.map((opt) => {
                            const isEditing = editingId === opt.id;
                            const isDefault = opt.is_default;

                            return (
                                <div
                                    key={opt.id}
                                    className={`rounded-[var(--radius-3)] border px-4 py-3 ${
                                        isDefault
                                            ? "border-primary bg-orange-50"
                                            : "border-dashed border-border bg-white"
                                    }`}
                                >
                                    {isEditing ? (
                                        <div>
                                            <div className="text-xs text-text-faint mb-1">Option name</div>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    className="flex-1 border border-border-input rounded px-2 py-1 text-sm focus:outline-none focus:ring-1"
                                                    value={editLabel}
                                                    onChange={(e) => setEditLabel(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === "Enter") handleEditConfirm(opt.id);
                                                        if (e.key === "Escape") { setEditingId(null); setEditLabel(""); }
                                                    }}
                                                    autoFocus
                                                />
                                                <button
                                                    className="text-success hover:text-green-700 cursor-pointer disabled:opacity-40"
                                                    onClick={() => handleEditConfirm(opt.id)}
                                                    disabled={loading || !editLabel.trim()}
                                                    aria-label="Confirm rename"
                                                >
                                                    <span className="material-symbols-rounded text-xl">check</span>
                                                </button>
                                                <button
                                                    className="text-text-table-cell cursor-pointer hover:text-text-base"
                                                    onClick={() => { setEditingId(null); setEditLabel(""); }}
                                                    aria-label="Cancel rename"
                                                >
                                                    <span className="material-symbols-rounded text-xl">close</span>
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm font-medium text-text-dark">{opt.label}</span>
                                            <div className="flex items-center gap-3">
                                                {isDefault ? (
                                                    <span className="text-xs bg-white border border-primary text-primary rounded-full px-2 py-1">
                                                        Base case
                                                    </span>
                                                ) : (
                                                    <button
                                                        className="text-sm text-text-table-cell font-medium hover:text-primary transition-colors cursor-pointer disabled:opacity-40"
                                                        onClick={() => handleSetDefault(opt.id)}
                                                        disabled={loading}
                                                    >
                                                        Set as base case
                                                    </button>
                                                )}
                                                <div className="relative">
                                                    <button
                                                        className="p-1 rounded hover:bg-neutral-100 transition-colors"
                                                        onClick={() => setOpenMenuId(openMenuId === opt.id ? null : opt.id)}
                                                        aria-label="Option actions"
                                                    >
                                                        <span className="material-symbols-rounded text-base">more_vert</span>
                                                    </button>
                                                    {openMenuId === opt.id && (
                                                        <div className="absolute right-0 mt-1 w-28 rounded-md border border-neutral-200 bg-white shadow-lg z-10 py-1">
                                                            <button
                                                                className="w-full text-left px-3 py-2 cursor-pointer text-sm text-text-base hover:bg-neutral-50 transition-colors"
                                                                onClick={() => {
                                                                    setEditingId(opt.id);
                                                                    setEditLabel(opt.label);
                                                                    setOpenMenuId(null);
                                                                }}
                                                            >
                                                                Edit
                                                            </button>
                                                            <button
                                                                className={`w-full text-left px-3 py-2 text-sm cursor-pointer transition-colors ${
                                                                    isDefault
                                                                        ? "text-text-table-cell cursor-not-allowed"
                                                                        : "text-danger hover:bg-neutral-50"
                                                                }`}
                                                                onClick={() => {
                                                                    if (isDefault) return;
                                                                    setDeleteTarget(opt);
                                                                    setOpenMenuId(null);
                                                                }}
                                                                disabled={isDefault}
                                                            >
                                                                Delete
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    <div className="flex justify-end gap-3 mt-6">
                        <button
                            className="px-6 py-2.5 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-neutral-50 transition-colors"
                            onClick={onClose}
                        >
                            Cancel
                        </button>
                        <button
                            className="bg-primary cursor-pointer text-white px-6 py-2.5 rounded-[var(--radius-3)] text-sm font-medium hover:bg-opacity-90 transition-colors"
                            onClick={onClose}
                        >
                            Save
                        </button>
                    </div>
                </div>
            </div>

            {deleteTarget && (
                <DeleteOptionModal
                    open={!!deleteTarget}
                    onClose={() => setDeleteTarget(null)}
                    option={deleteTarget}
                    onDeleted={async () => {
                        setDeleteTarget(null);
                        await onOptionsChange();
                    }}
                />
            )}
        </>
    );
}
