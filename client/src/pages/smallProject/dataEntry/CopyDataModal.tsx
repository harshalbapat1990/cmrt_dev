import { useState } from "react";
import ProjectOptionsService from "@/services/ProjectOptions.service";

interface Option {
    label: string;
    value: string;
}

interface Props {
    open: boolean;
    onClose: () => void;
    currentOptionId: string;
    options: Option[];
    onCopied: () => void;
}

export default function CopyDataModal({
    open,
    onClose,
    currentOptionId,
    options,
    onCopied,
}: Props) {
    const [selectedSourceId, setSelectedSourceId] = useState<string>("");
    const [step, setStep] = useState<"select" | "confirm">("select");
    const [loading, setLoading] = useState(false);

    if (!open) return null;

    const sourceOptions = options.filter((o) => o.value !== currentOptionId);
    const currentOptionName = options.find((o) => o.value === currentOptionId)?.label ?? "Current option";
    const sourceOptionName = options.find((o) => o.value === selectedSourceId)?.label ?? "";

    const handleClose = () => {
        setStep("select");
        setSelectedSourceId("");
        onClose();
    };

    const handleCopy = async () => {
        if (!selectedSourceId) return;
        setLoading(true);
        try {
            await ProjectOptionsService.copyOption(selectedSourceId, currentOptionId);
            onCopied();
            handleClose();
        } catch (e) {
            console.error("Failed to copy option data:", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full mx-4">
                {step === "select" ? (
                    <>
                        <h2 className="text-2xl text-text-dark mb-5">Copy data</h2>

                        <p className="text-sm text-text-base mb-4">
                            Copying data into{" "}
                            <span className="font-semibold">{currentOptionName}</span>{" "}
                            <span className="text-text-faint">(current option)</span>
                        </p>

                        <div className="mb-6">
                            <label className="block text-base text-text-base mb-2">
                                Choose the option you'd like to copy data from:
                            </label>
                            {sourceOptions.length === 0 ? (
                                <p className="text-sm text-text-faint italic">No other options available to copy from.</p>
                            ) : (
                                <select
                                    className="w-full border border-border-input rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                                    value={selectedSourceId}
                                    onChange={(e) => setSelectedSourceId(e.target.value)}
                                >
                                    <option value="" disabled>
                                        — Select an option —
                                    </option>
                                    {sourceOptions.map((opt) => (
                                        <option key={opt.value} value={opt.value}>
                                            {opt.label}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>

                        <div className="flex justify-end gap-3">
                            <button
                                className="px-6 py-2.5 rounded-[var(--radius-3)] cursor-pointer text-sm font-medium text-text-table-cell hover:bg-neutral-50 transition-colors disabled:opacity-40"
                                onClick={handleClose}
                            >
                                Cancel
                            </button>
                            <button
                                className="bg-primary text-white px-6 py-2.5 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-opacity-90 transition-colors disabled:opacity-40"
                                onClick={() => setStep("confirm")}
                                disabled={!selectedSourceId || sourceOptions.length === 0}
                            >
                                Copy data
                            </button>
                        </div>
                    </>
                ) : (
                    <>
                        <h2 className="text-2xl text-text-dark mb-5">Confirm copy</h2>

                        <div className="flex items-center gap-3 mb-6">
                            <div className="border border-border-input rounded px-4 py-2 text-sm">
                                {sourceOptionName}
                            </div>
                            <span className="material-symbols-rounded text-text-faint text-xl">arrow_forward</span>
                            <div className="border-2 border-primary bg-primary/5 rounded px-4 py-2 text-sm font-medium">
                                {currentOptionName}{" "}
                                <span className="text-text-faint font-normal">(current)</span>
                            </div>
                        </div>

                        <div className="flex items-start gap-2 bg-[#FFF3DB] border border-[#53400159] rounded-[var(--radius-3)] px-4 py-3 mb-6">
                            <span className="material-symbols-rounded text-[#534001] text-base mt-0.5">warning</span>
                            <p className="text-sm text-[#534001]">
                                All data from <strong>{sourceOptionName}</strong> will be copied into{" "}
                                <strong>{currentOptionName}</strong>. Any existing data in{" "}
                                <strong>{currentOptionName}</strong> will be{" "}
                                <strong>overwritten</strong> and cannot be recovered.
                            </p>
                        </div>

                        <div className="flex justify-end gap-3">
                            <button
                                className="px-6 py-2.5 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium text-text-table-cell hover:bg-neutral-50 transition-colors disabled:opacity-40"
                                onClick={() => setStep("select")}
                                disabled={loading}
                            >
                                Back
                            </button>
                            <button
                                className="bg-primary text-white px-6 py-2.5 rounded-[var(--radius-3)] cursor-pointer text-sm font-medium hover:bg-opacity-90 transition-colors disabled:opacity-40"
                                onClick={handleCopy}
                                disabled={loading}
                            >
                                {loading ? "Copying…" : "Confirm copy"}
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
