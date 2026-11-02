import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Modal } from "@/components/common/Modal";
import SteppedProgressBar from "@/components/common/SteppedProgressBar";
import { getMitigationPanelBaseKeys } from "../mitigationConstants";
import { MITIGATION_LIFECYCLE_PHASE_LABEL as LIFECYCLE_PHASE_LABEL, MITIGATION_TYPE_LABEL as TYPE_LABEL } from "../mitigationTypes";
import type { MitigationLifecyclePhase, MitigationType } from "../mitigationTypes";
import type { DataEntryRow } from "../dataEntryTypes";
import type { MitigationHydrate, MitigationPersistenceApi, MitigationTablesCollector, MitigationWizardSnapshot, StageName } from "../Mitigations";
import type { Step1Form } from "./MitigationStepOne";
export type TablePanelRenderOptions = {
  leg: "replaced" | "adopted" | null;
  collectorRef: React.MutableRefObject<MitigationTablesCollector | null>;
  hydrateTables: Record<string, DataEntryRow[]> | null;
  scopeKey: string;
};

export const Step2Modal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  draft: Step1Form | null;
  submissionStage: StageName;
  mitigationScenarioId: string | null;
  persistence: MitigationPersistenceApi | null;
  hydrateSnapshot: MitigationHydrate | null;
  detailReadOnly: boolean;
  tablesCollectorRef: React.MutableRefObject<{
    collect: () => MitigationWizardSnapshot;
  } | null>;
  onPersisted: () => void | Promise<void>;
  renderTables: (options: TablePanelRenderOptions) => React.ReactNode;
}> = ({
  isOpen,
  onClose,
  draft,
  submissionStage,
  mitigationScenarioId,
  persistence,
  hydrateSnapshot,
  detailReadOnly,
  tablesCollectorRef,
  onPersisted,
  renderTables,
}) => {
  const isSubstitution = draft?.type === "substitution";
  const innerCollectorRef = useRef<MitigationTablesCollector | null>(null);
  const replacedCollectorRef = useRef<MitigationTablesCollector | null>(
    null,
  );
  const adoptedCollectorRef = useRef<MitigationTablesCollector | null>(null);

  const [subStep, setSubStep] = useState<1 | 2>(1);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) setSubStep(1);
  }, [isOpen]);

  useLayoutEffect(() => {
    tablesCollectorRef.current = {
      collect: () => {
        if (draft?.type === "substitution") {
          return {
            mode: "substitution",
            replaced: replacedCollectorRef.current?.collect() ?? {},
            adopted: adoptedCollectorRef.current?.collect() ?? {},
          };
        }
        return {
          mode: "reduction",
          tables: innerCollectorRef.current?.collect() ?? {},
        };
      },
    };
  }, [draft?.type, draft?.lifecyclePhase, submissionStage, tablesCollectorRef]);

  const handleSaveMitigation = async () => {
    if (
      detailReadOnly ||
      !draft?.lifecyclePhase ||
      !mitigationScenarioId ||
      !persistence
    ) {
      return;
    }
    setSaving(true);
    try {
      const snap = tablesCollectorRef.current?.collect();
      if (!snap) {
        return;
      }
      const keys = getMitigationPanelBaseKeys(
        submissionStage,
        draft.lifecyclePhase as MitigationLifecyclePhase,
      );
      if (snap.mode === "reduction") {
        for (const k of keys) {
          await persistence.saveMitigationBulkTable(
            k,
            mitigationScenarioId,
            snap.tables[k] ?? [],
          );
        }
      } else {
        for (const k of keys) {
          await persistence.saveMitigationBulkTable(
            k,
            mitigationScenarioId,
            snap.replaced[k] ?? [],
            "replaced",
          );
          await persistence.saveMitigationBulkTable(
            k,
            mitigationScenarioId,
            snap.adopted[k] ?? [],
            "adopted",
          );
        }
      }
      await persistence.patchMitigationMeta(mitigationScenarioId, {
        name: draft.name.trim(),
        type: draft.type || "reduction",
        lifecyclePhase: draft.lifecyclePhase,
        lifecyclePhaseLabel:
          LIFECYCLE_PHASE_LABEL[draft.lifecyclePhase as MitigationLifecyclePhase],
        notes: draft.notes?.trim(),
        group: draft.group?.trim(),
        submissionStage,
      });
      await onPersisted();
      onClose();
    } catch (e) {
      console.warn("Mitigation save failed:", e);
    } finally {
      setSaving(false);
    }
  };

  if (!draft) return null;

  const subTitle = isSubstitution
    ? subStep === 1
      ? "Source(s) replaced"
      : "Source(s) adopted"
    : "";

  const reductionHydrate =
    hydrateSnapshot?.kind === "reduction" ? hydrateSnapshot.tables : null;
  const substReplacedHydrate =
    hydrateSnapshot?.kind === "substitution"
      ? hydrateSnapshot.replaced
      : null;
  const substAdoptedHydrate =
    hydrateSnapshot?.kind === "substitution" ? hydrateSnapshot.adopted : null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="New mitigation"
      className="max-w-[1280px] mx-4 my-6"
    >
      <div className="flex flex-col h-[90vh]">
        <div className="flex items-center justify-between px-8 py-4 border-b border-neutral-90">
          <div>
            <div className="text-2xl text-text-dark">{draft.name}</div>
            <div className="text-sm text-text-faint mt-0.5">
              {TYPE_LABEL[draft.type as MitigationType]}
              {draft.group ? ` • ${draft.group}` : ""}
              {subTitle ? ` • ${subTitle}` : ""}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-base  cursor-pointer hover:bg-neutral-95 p-1 rounded transition-colors"
            aria-label="Close"
          >
            <span className="material-symbols-rounded">close</span>
          </button>
        </div>

        {isSubstitution && (
          <div className="px-8 pt-5 pb-2">
            <SteppedProgressBar
              steps={["Source(s) replaced", "Source(s) adopted"]}
              currentStep={subStep}
            />
          </div>
        )}

        <div
          key={mitigationScenarioId ?? "new-scenario"}
          className="flex-1 overflow-y-auto bg-neutral-98"
        >
          {isSubstitution ? (
            <>
              <div className={subStep === 1 ? "block" : "hidden"}>
                {renderTables({ leg: "replaced", collectorRef: replacedCollectorRef, hydrateTables: substReplacedHydrate, scopeKey: (mitigationScenarioId ?? "new") + "-" + draft.lifecyclePhase + "-replaced" })}
              </div>
              <div className={subStep === 2 ? "block" : "hidden"}>
                {renderTables({ leg: "adopted", collectorRef: adoptedCollectorRef, hydrateTables: substAdoptedHydrate, scopeKey: (mitigationScenarioId ?? "new") + "-" + draft.lifecyclePhase + "-adopted" })}
              </div>
            </>
          ) : renderTables({
            leg: null,
            collectorRef: innerCollectorRef,
            hydrateTables: reductionHydrate,
            scopeKey: (mitigationScenarioId ?? "new") + "-" + draft.lifecyclePhase,
          })}
        </div>

        <div className="flex justify-between items-center gap-3 px-8 py-4 border-t border-neutral-90 bg-white">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 cursor-pointer text-sm rounded-[var(--radius-3)] border border-border-input text-text-base hover:bg-neutral-95"
          >
            {detailReadOnly ? "Close" : "Cancel"}
          </button>
          {!detailReadOnly && (
            <div className="flex items-center gap-3">
              {isSubstitution && subStep === 2 && (
                <button
                  type="button"
                  onClick={() => setSubStep(1)}
                  className="px-4 py-2 text-sm  cursor-pointer rounded-[var(--radius-3)] border border-border-input text-text-base hover:bg-neutral-95"
                >
                  Back
                </button>
              )}
              {isSubstitution && subStep === 1 ? (
                <button
                  type="button"
                  onClick={() => setSubStep(2)}
                  className="px-4 py-2 text-sm cursor-pointer rounded-[var(--radius-3)] bg-primary text-white hover:bg-primary/90"
                >
                  Next
                </button>
              ) : (
                <button
                  type="button"
                  disabled={saving || !persistence || !mitigationScenarioId}
                  onClick={() => void handleSaveMitigation()}
                  className="px-4 py-2 text-sm rounded-[var(--radius-3)] bg-primary cursor-pointer text-white hover:bg-primary/90 disabled:opacity-40"
                >
                  Save mitigation
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};

