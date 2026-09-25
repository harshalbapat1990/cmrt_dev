type AdminDecisionType = "approve" | "reject" | "approveReopen" | "denyReopen";

interface AdminDecisionModalProps {
    open: boolean;
    adminDecisionOpen: AdminDecisionType | null;
    decisionComments: string;
    onDecisionCommentsChange: (value: string) => void;
    onClose: () => void;
    onConfirm: () => void;
}

export function AdminDecisionModal({
    open,
    adminDecisionOpen,
    decisionComments,
    onDecisionCommentsChange,
    onClose,
    onConfirm,
}: AdminDecisionModalProps) {
    if (!open) return null;

    const title =
        adminDecisionOpen === "approve" ? "Approve submission" :
        adminDecisionOpen === "reject" ? "Reject submission" :
        adminDecisionOpen === "approveReopen" ? "Approve reopen request" :
        adminDecisionOpen === "denyReopen" ? "Deny reopen request" : "";

    const requiresJustification =
        adminDecisionOpen === "reject" || adminDecisionOpen === "denyReopen";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-lg w-full mx-4">
                <div className="text-2xl text-text-dark mb-6">{title}</div>
                <div className="mb-6">
                    <label className="text-sm font-medium text-text-dark">
                        {requiresJustification ? "Justification (required)" : "Justification (optional)"}
                    </label>
                    <textarea
                        className="border border-border-input w-full rounded-[var(--radius-3)] h-28 p-3 mt-2"
                        value={decisionComments}
                        onChange={(e) => onDecisionCommentsChange(e.target.value)}
                    />
                    <div className="text-right mt-4">
                        <button
                            className="border border-neutral-300 px-4 py-2 cursor-pointer rounded mr-2"
                            onClick={onClose}
                        >Cancel</button>
                        <button
                            className="bg-primary text-white px-4 py-2 cursor-pointer rounded disabled:opacity-60"
                            disabled={requiresJustification && !decisionComments.trim()}
                            onClick={onConfirm}
                        >
                            Confirm
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
