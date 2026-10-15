import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Modal } from "@/components/common/Modal";
import { SelectListbox } from "@/components/common/Select";
import type { MitigationLifecyclePhase, MitigationType } from "../mitigationTypes";

type StageName = "Design" | "Construction";
export type Step1Form = {
  name: string;
  type: MitigationType | "";
  group: string;
  notes: string;
  lifecyclePhase: MitigationLifecyclePhase | "";
};

const LIFECYCLE_PHASE_OPTIONS: { label: string; value: MitigationLifecyclePhase }[] = [
  { label: "Construction", value: "construction" },
  { label: "Operations & Maintenance", value: "operations_maintenance" },
  { label: "Users", value: "users" },
];

const TYPE_OPTIONS = [
  { label: "Avoidance/Reduction Initiative", value: "reduction" },
  { label: "Substitution Initiative", value: "substitution" },
];

export const Step1Modal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onNext: (form: Step1Form) => void | Promise<void>;
  submissionStage: StageName;
}> = ({ isOpen, onClose, onNext, submissionStage }) => {
  const [form, setForm] = useState<Step1Form>({
    name: "",
    type: "",
    group: "",
    notes: "",
    lifecyclePhase: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const lifecyclePhaseOptions = useMemo(
    () =>
      submissionStage === "Construction"
        ? LIFECYCLE_PHASE_OPTIONS.filter((o) => o.value !== "users")
        : LIFECYCLE_PHASE_OPTIONS,
    [submissionStage],
  );

  useEffect(() => {
    if (!isOpen) return;
    setForm((f) =>
      f.lifecyclePhase === "users" && submissionStage === "Construction"
        ? { ...f, lifecyclePhase: "" }
        : f,
    );
  }, [isOpen, submissionStage]);

  const handleNext = async () => {
    if (!form.name.trim()) {
      setError("Mitigation name is required.");
      return;
    }
    if (!form.lifecyclePhase) {
      setError("Project stage is required.");
      return;
    }
    if (!form.type) {
      setError("Mitigation type is required.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await onNext(form);
      setForm({
        name: "",
        type: "",
        group: "",
        notes: "",
        lifecyclePhase: "",
      });
    } catch (e) {
      console.warn("Mitigation draft create failed:", e);
      setError("Could not create mitigation. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const handleClose = useCallback(() => {
    setError(null);
    setForm({
      name: "",
      type: "",
      group: "",
      notes: "",
      lifecyclePhase: "",
    });
    onClose();
  }, [onClose]);

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="New mitigation" className="max-w-lg">
      <div className="px-6 pt-6 pb-2">
        <div className="text-2xl text-text-dark mb-1">New mitigation</div>

        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-text-base mb-1">
              Name <span className="text-danger">*</span>
            </label>
            <input
              className="w-full h-10 bg-white border border-border-input rounded-[var(--radius-3)] px-3 text-sm"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Replace concrete with timber"
            />
          </div>

          <div>
            <label className="block text-sm text-text-base mb-1">
              Project stage <span className="text-danger">*</span>
            </label>
            <SelectListbox
              value={form.lifecyclePhase}
              onChange={(value: string) =>
                setForm((f) => ({
                  ...f,
                  lifecyclePhase: value as MitigationLifecyclePhase,
                }))
              }
              options={lifecyclePhaseOptions}
              placeholder="Select project stage"
            />
          </div>

          <div>
            <label className="block text-sm text-text-base mb-1">
              Type <span className="text-danger">*</span>
            </label>
            <SelectListbox
              value={form.type}
              onChange={(value: string) =>
                setForm((f) => ({ ...f, type: value as MitigationType }))
              }
              options={TYPE_OPTIONS}
              placeholder="Select type"
            />
          </div>

          <div>
            <label className="block text-sm text-text-base mb-1">
              Grouping <span className="text-text-faint">(optional)</span>
            </label>
            <input
              className="w-full h-10 bg-white border border-border-input rounded-[var(--radius-3)] px-3 text-sm"
              value={form.group}
              onChange={(e) => setForm((f) => ({ ...f, group: e.target.value }))}
            />
          </div>

          <div>
            <label className="block text-sm text-text-base mb-1">
              Notes <span className="text-text-faint">(optional)</span>
            </label>
            <textarea
              className="w-full bg-white border border-border-input rounded-[var(--radius-3)] px-3 py-2 text-sm h-24"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </div>

          {error && <div className="text-sm text-danger">{error}</div>}
        </div>
      </div>

      <div className="flex justify-end items-center gap-3 px-6 py-4 border-t border-neutral-90 mt-4">
        <button
          type="button"
          onClick={handleClose}
          className="px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] border border-border-input text-text-base hover:bg-neutral-95"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => void handleNext()}
          disabled={busy}
          className="px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] bg-primary text-white hover:bg-primary/90 disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </Modal>
  );
};

