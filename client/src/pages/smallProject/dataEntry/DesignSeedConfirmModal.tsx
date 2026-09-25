interface DesignSeedConfirmModalProps {
    open: boolean;
    pendingDesignReportNum: number | null;
    reDesignSeedLoading: boolean;
    onCancel: () => void;
    onConfirm: () => Promise<void>;
}

export function DesignSeedConfirmModal({
    open,
    pendingDesignReportNum,
    reDesignSeedLoading,
    onCancel,
    onConfirm,
}: DesignSeedConfirmModalProps) {
    if (!open || pendingDesignReportNum === null) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-lg shadow-xl p-6 w-[480px] max-w-full">
                <h3 className="text-lg font-semibold mb-2">Change Design Report</h3>
                <p className="text-sm text-text-base mb-6">
                    Switching to <strong>Design Report {pendingDesignReportNum}</strong> will replace all{" "}
                    <strong>Use (B1)</strong>, <strong>Operations &amp; Maintenance</strong>, and{" "}
                    <strong>Operational Energy</strong> data for <strong>all Construction periods</strong>.
                    This cannot be undone.
                </p>
                <div className="flex justify-end gap-3">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="px-4 py-2 text-sm border cursor-pointer border-neutral-300 rounded hover:bg-neutral-100"
                    >Cancel</button>
                    <button
                        type="button"
                        disabled={reDesignSeedLoading}
                        onClick={onConfirm}
                        className="px-4 py-2 text-sm bg-primary text-white cursor-pointer rounded hover:bg-primary-dark disabled:opacity-50"
                    >{reDesignSeedLoading ? "Updating…" : "Confirm"}</button>
                </div>
            </div>
        </div>
    );
}
