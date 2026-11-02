import React, { useEffect, useRef, useState } from "react";
import type { AdminAccessRequest } from "../types/access";
import alertIconUrl from "../assets/icons/emergency_home.svg";

type Props = {
  open: boolean;
  request: AdminAccessRequest | null;
  formerror: string;
  onClose: () => void;
  onApprove: (r: AdminAccessRequest) => void;
  onReject: (r: AdminAccessRequest, reason: string) => void;
};

const ReviewModal: React.FC<Props> = ({
  open,
  request,
  formerror,
  onClose,
  onApprove,
  onReject
}) => {
  const [reason, setReason] = useState("");
  const [showReject, setShowReject] = useState(false);
  const [error, setError] = useState("");
  const [showRejectBtn, setShowRejectBtn] = useState(true);
  const [showApprove, setShowApprove] = useState(true);
  const backdropRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Helpers
  const PROJECT_CLASS_LABELS: Record<string, string> = {
    SMALL: "Small",
    LARGE: "Large",
    RECURRING: "Recurring",
  };
  const isRecurring = (cat?: string) =>
    !cat || cat.trim().toUpperCase() === "RECURRING";
  const safeStages =
    (request?.stages && Array.isArray(request.stages) ? request.stages : []) as
      | { name: string; access: string }[]
      | [];

  const normalizeProjectCategory = (cat?: string) => {
    if (!cat || !cat.trim()) return "";
    return PROJECT_CLASS_LABELS[cat.trim().toUpperCase()] ?? cat;
  };
  const derivedAccess =
    request?.requestedRole === "PROJECT_EDITOR"
      ? "Edit"
      : request?.requestedRole === "PROJECT_VIEWER"
      ? "View"
      : request?.requestedRole === "PROJECT_ADMIN"
      ? "Admin"
      : "View";

  useEffect(() => {
    if (open) {
      setReason("");
      setShowReject(false);
      setError("");
      // Reset buttons every time the modal opens
      setShowRejectBtn(true);
      setShowApprove(true);
    }
  }, [open]);

  useEffect(() => {
    if (showReject) textareaRef.current?.focus();
  }, [showReject]);

  if (!open || !request) return null;

  const handleBackdrop = (e: React.MouseEvent) => {
    if (e.target === backdropRef.current) onClose();
  };

  const handleRejectClick = () => {
    if (!showReject) {
      setShowReject(true);
      setShowApprove(false);
      setShowRejectBtn(false);
      return;
    }
    
    if (validateReason()) {
      onReject(request, reason.trim());
    }
  };

  const validateReason = () => {
    if (!reason.trim()) {
      setError(formerror);
      return false;
    }
    setError("");
    return true;
  };



  return (
    <div
      ref={backdropRef}
      onClick={handleBackdrop}
      className="fixed inset-0 z-50 flex items-center  justify-center bg-black/30 cursor-pointer"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-lg rounded-[var(--radius-3)] bg-white p-6 shadow-xl">
        <h3 className="mb-6 text-2xl font-normal text-text-dark">Review access request</h3>

        <div className="mb-4">
          <label className="mb-2 block text-xs font-medium text-text-faint">REQUESTED BY</label>
          <span className="text-sm text-text-table-cell">{request.requester}</span>
        </div>

        <div className="mb-4">
          <label className="mb-2 block text-xs font-medium text-text-faint">PROJECT NAME</label>
          <span className="text-sm text-text-table-cell">{request.projectName}</span>
        </div>

        <div className="mb-4">
          <label className="mb-2 block text-xs font-medium text-text-faint">PROJECT CATEGORY</label>
         <span className="text-sm text-text-table-cell">{normalizeProjectCategory(request.projectCategory)}</span>
        </div>

        
        {!isRecurring(request.projectCategory) ? (
          // Non-recurring category: show stages (if any)
          safeStages.length > 0 ? (
            <div className="mt-4 space-y-2">
              <div className="text-sm text-slate-700">
                <label className="mb-1 block text-xs font-medium text-text-faint">
                  PROJECT STAGE AND ACCESS
                </label>
                <div className="mb-4 mt-2 space-y-3">
                  {safeStages.map((s, i) => (
                    <div
                      key={`${s.name}-${i}`}
                      className="flex items-center gap-13 rounded-md border border-[#F3F3F3] bg-neutral-98 px-4 py-4 mb-2"
                    >
                      <span className="text-sm text-text-table-cell w-30 font-normal">{s.name}</span>
                      <span className="rounded-full border border-neutral-90 bg-white px-3 py-1 text-xs font-medium text-[#5A5A5A]">
                        {s.access}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null
        ) : (
          // Recurring category: no stages, show a single ACCESS pill
          <div className="mt-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-text-faint">ACCESS</label>
              <span className="inline-flex items-center rounded-full border border-neutral-90 bg-slate-50 px-3 py-1 text-xs font-medium text-[#5A5A5A]">
                {derivedAccess}
              </span>
            </div>
          </div>
        )}

        {/* Justification (if any) */}
        {request.justification && (
          <div className="mt-4 text-sm text-slate-700 mb-8">
            <label className="mb-1 block text-xs font-medium text-text-faint">JUSTIFICATION</label>
            <span className="bg-info-bg block p-4 text-info-text">{request.justification}</span>
          </div>
        )}

        {/* Rejection reason textarea (two-step reject) */}
        {showReject && (
          
          <div className="mt-5">
             <div className="mb-4">
              <div className="h-px bg-gray-100"></div>
            </div>
            <label className="mb-1 block text-xs font-medium text-text-faint">
              REASON FOR REJECTION (REQUIRED)
            </label>
            <textarea
              ref={textareaRef}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                setError(""); // Clear error on change
              }}
              required
             
              className={
                  `h-40 w-full rounded-[var(--radius-3)] border-2 px-3 py-2 text-sm outline-none
                  ${error
                    ? 'border-danger border-2'
                    : 'border-border-input'
                  }`
                }

              rows={3}
              placeholder=""
            />
            {error && (
              <div
                role="alert"
                aria-live="assertive"
                className="mb-2 mt-1 flex items-center gap-1.5 text-sm text-danger"
              >
                <img src={alertIconUrl} alt="" width={20} height={20} aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}

          </div>
        )}

        {/* Footer actions */}
        <div className="mt-6 flex justify-start gap-55">
          <button
            onClick={onClose}
            className=" bg-white px-4 py-2 text-sm text-text-table-cell cursor-pointer "
          >
            Cancel
          </button>

          <div className="flex gap-3">
            {showRejectBtn ? (
              <button
                onClick={handleRejectClick}
                className="rounded border border-text-table-cell bg-white px-4 py-2 text-sm text-text-table-cell cursor-pointer"
              >
                Reject
              </button>
            ) : (
              <button
                onClick={handleRejectClick}
                className="rounded ml-9 border border-primary bg-primary px-4 py-2 text-sm font-medium text-white cursor-pointer"
              >
                Confirm Reject
              </button>
            )}

            {showApprove ? (
              <button
                onClick={() => onApprove(request)}
                className="rounded bg-primary px-4 py-2 text-sm font-medium text-white cursor-pointer"
              >
                Approve
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewModal;

