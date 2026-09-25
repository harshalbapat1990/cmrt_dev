import React, { useEffect, useRef, useState } from "react";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";

type WorkflowAction =
    | "submit"
    | "approve"
    | "reject"
    | "requestReopen"
    | "approveReopen"
    | "rejectReopen";

interface PeriodWorkflowModalProps {
    open: boolean;
    action: WorkflowAction | null;
    period: ConstructionPeriod | null;
    onConfirm: (reason?: string) => Promise<void>;
    onCancel: () => void;
}

const ACTION_CONFIG: Record<
    WorkflowAction,
    { title: string; description: string; confirmLabel: string; reasonLabel?: string; reasonRequired: boolean; confirmClass: string }
> = {
    submit: {
        title: "Submit Period for Approval",
        description: "This will submit the period for review. You will not be able to edit entries until an outcome is received.",
        confirmLabel: "Submit",
        reasonRequired: false,
        confirmClass: "bg-primary hover:bg-primary-700 text-white",
    },
    approve: {
        title: "Approve Period",
        description: "Approving this period will lock the data and automatically create the next period.",
        confirmLabel: "Approve",
        reasonRequired: false,
        confirmClass: "bg-green-600 hover:bg-green-700 text-white",
    },
    reject: {
        title: "Reject Period",
        description: "Rejecting will return the period to the editor for corrections.",
        confirmLabel: "Reject",
        reasonLabel: "Reason for rejection",
        reasonRequired: true,
        confirmClass: "bg-red-600 hover:bg-red-700 text-white",
    },
    requestReopen: {
        title: "Request Period Reopen",
        description: "This will send a reopen request to an admin. The period remains locked until the request is approved.",
        confirmLabel: "Send Request",
        reasonLabel: "Reason for reopening",
        reasonRequired: true,
        confirmClass: "bg-primary-600 hover:bg-primary-700 text-white",
    },
    approveReopen: {
        title: "Approve Reopen Request",
        description: "Approving this request will unlock the period for editing.",
        confirmLabel: "Approve Reopen",
        reasonRequired: false,
        confirmClass: "bg-green-600 hover:bg-green-700 text-white",
    },
    rejectReopen: {
        title: "Reject Reopen Request",
        description: "Rejecting this request will keep the period locked.",
        confirmLabel: "Reject Request",
        reasonLabel: "Reason for rejecting reopen",
        reasonRequired: true,
        confirmClass: "bg-red-600 hover:bg-red-700 text-white",
    },
};

const PeriodWorkflowModal: React.FC<PeriodWorkflowModalProps> = ({
    open,
    action,
    period,
    onConfirm,
    onCancel,
}) => {
    const [reason, setReason] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const backdropRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (open) {
            setReason("");
            setError("");
            setLoading(false);
        }
    }, [open]);

    useEffect(() => {
        if (open && config?.reasonRequired) {
            setTimeout(() => textareaRef.current?.focus(), 50);
        }
    }, [open]);

    if (!open || !action || !period) return null;

    const config = ACTION_CONFIG[action];

    const handleBackdrop = (e: React.MouseEvent) => {
        if (e.target === backdropRef.current) onCancel();
    };

    const handleConfirm = async () => {
        if (config.reasonRequired && !reason.trim()) {
            setError(`${config.reasonLabel ?? "Reason"} is required.`);
            return;
        }
        setError("");
        setLoading(true);
        try {
            await onConfirm(reason.trim() || undefined);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            ref={backdropRef}
            onClick={handleBackdrop}
            className="fixed inset-0 z-50 flex cursor-pointer items-center justify-center bg-black/30"
            role="dialog"
            aria-modal="true"
        >
            <div className="w-full max-w-md rounded-[var(--radius-3)] bg-white p-6 shadow-xl">
                <h3 className="mb-1 text-xl font-normal text-text-dark">{config.title}</h3>
                <p className="mb-1 text-xs text-text-faint">
                    Period: <span className="font-medium text-text-base">{period.period_label}</span>
                </p>
                <p className="mb-5 text-sm text-text-base">{config.description}</p>

                {config.reasonLabel !== undefined && (
                    <div className="mb-4">
                        <label className="mb-1 block text-sm font-medium text-text-base">
                            {config.reasonLabel}
                            {config.reasonRequired && (
                                <span className="ml-1 text-red-600">*</span>
                            )}
                        </label>
                        <textarea
                            ref={textareaRef}
                            className={`w-full rounded-[var(--radius-3)] border p-3 text-sm outline-none focus:ring-2 focus:ring-border-input focus:border-transparent resize-none h-24 ${
                                error ? "border-red-400" : "border-border-input"
                            }`}
                            value={reason}
                            onChange={(e) => {
                                setReason(e.target.value);
                                if (error) setError("");
                            }}
                            placeholder={`Enter ${(config.reasonLabel ?? "reason").toLowerCase()}…`}
                        />
                        {error && (
                            <p className="mt-1 text-xs text-red-600">{error}</p>
                        )}
                    </div>
                )}

                <div className="flex justify-end gap-3">
                    <button
                        className="px-4 py-2 text-sm rounded-[var(--radius-3)] border cursor-pointer border-neutral-90 text-text-base hover:bg-neutral-98 disabled:opacity-50"
                        onClick={onCancel}
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button
                        className={`px-4 py-2 text-sm rounded-[var(--radius-3)] disabled:opacity-50 cursor-pointer ${config.confirmClass}`}
                        onClick={handleConfirm}
                        disabled={loading}
                    >
                        {loading ? "Processing…" : config.confirmLabel}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PeriodWorkflowModal;
