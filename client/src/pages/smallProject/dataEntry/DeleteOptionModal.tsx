import { useState } from "react";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import ProjectOptionsService from "@/services/ProjectOptions.service";

interface Props {
    open: boolean;
    onClose: () => void;
    option: ProjectOption | null;
    onDeleted: () => void;
}

export default function DeleteOptionModal({ open, onClose, option, onDeleted }: Props) {
    const [loading, setLoading] = useState(false);

    if (!open || !option) return null;

    const handleDelete = async () => {
        setLoading(true);
        try {
            await ProjectOptionsService.deleteOption(option.id);
            onDeleted();
        } catch (e) {
            console.error("Failed to delete option:", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full mx-4">
                <div className="flex items-start gap-3 mb-4">
                    <span className="material-symbols-rounded text-2xl text-danger mt-0.5">warning</span>
                    <h2 className="text-2xl font-semibold text-text-dark">Delete option</h2>
                </div>

                <p className="text-sm text-text-base leading-relaxed mb-6">
                    You're about to delete{" "}
                    <span className="font-medium">{option.label}</span>. All associated
                    data inputs with this option will be permanently removed and cannot be recovered.
                </p>
                <p className="text-sm text-text-base leading-relaxed mb-12">
                    Do you want to proceed?
                </p>

                <div className="flex justify-end gap-3">
                    <button
                        className="px-6 py-2.5 rounded-[var(--radius-3)] text-sm font-medium hover:bg-neutral-50 transition-colors cursor-pointer disabled:opacity-40"
                        onClick={onClose}
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button
                        className="px-6 py-2.5 rounded-[var(--radius-3)] text-sm font-medium bg-danger text-white transition-colors cursor-pointer disabled:opacity-40"
                        onClick={handleDelete}
                        disabled={loading}
                    >
                        {loading ? "Deleting…" : "Yes, delete this option"}
                    </button>
                </div>
            </div>
        </div>
    );
}
