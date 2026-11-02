import type { Dispatch, SetStateAction } from "react";
import { UploadModal } from "@/pages/dummy-table/UploadModal";
import ConfirmDeleteRowModal from "../ConfirmDeleteRowModal";
import { DesignSeedConfirmModal } from "../DesignSeedConfirmModal";
import ConcreteMixModal from "../ConcreteMixModal";
import { AdminDecisionModal } from "../AdminDecisionModal";
import { SimpleModal } from "./SimpleModal";
import ManageOptionsModal from "../ManageOptionsModal";
import CopyDataModal from "../CopyDataModal";
import PeriodWorkflowModal from "../PeriodWorkflowModal";
import type { AdminDecisionAction, PeriodWorkflowAction } from "../hooks/useWorkflowActions";
import type { ConstructionPeriod } from "@/services/ConstructionPeriods.service";
import type { ProjectOption } from "@/services/ProjectOptions.service";
import type { UploadKey } from "../stageConstants";
import type { DataEntryRow, StageInstance, StageLabel, TableRowMap } from "../dataEntryTypes";

type SelectOption = { label: string; value: string };

interface DataEntryModalsProps {
    uploadTarget: UploadKey | null;
    setUploadTarget: (v: UploadKey | null) => void;
    parseFile: (file: File, key: UploadKey) => Promise<DataEntryRow[]>;
    validateUpload: (rows: DataEntryRow[], key: UploadKey) => Promise<{ validRows: DataEntryRow[]; errors: string[] }>;
    onUploadSuccess: (rows: DataEntryRow[], key: UploadKey) => void | Promise<void>;
    deleteTarget: { id: string; tableKey: UploadKey } | null;
    setDeleteTarget: (v: { id: string; tableKey: UploadKey } | null) => void;
    doDeleteRow: () => Promise<void>;
    designSeedConfirmOpen: boolean;
    pendingDesignReportNum: number | null;
    reDesignSeedLoading: boolean;
    onCancelDesignSeed: () => void;
    onConfirmDesignSeed: () => Promise<void>;
    addLargeYearOpen: boolean;
    addLargeYearInput: string;
    addLargeYearError: string | null;
    setAddLargeYearOpen: (v: boolean) => void;
    setAddLargeYearInput: (v: string) => void;
    setAddLargeYearError: (v: string | null) => void;
    handleAddLargeYear: () => Promise<void>;
    copyLargeYearConfirmOpen: boolean;
    copyLargeYearSource: number | null;
    activeLargeUsersYear: number | null;
    largeUsersYears: number[];
    setCopyLargeYearConfirmOpen: (v: boolean) => void;
    setCopyLargeYearSource: (v: number | null) => void;
    handleCopyLargeYear: () => Promise<void>;
    deleteLargeYearConfirmOpen: boolean;
    setDeleteLargeYearConfirmOpen: (v: boolean) => void;
    handleDeleteLargeYear: () => Promise<void>;
    concreteMixModalType: "mix_design" | "epd_pcf" | null;
    setConcreteMixModalType: (v: "mix_design" | "epd_pcf" | null) => void;
    concreteMixEditTarget: DataEntryRow | null;
    setConcreteMixEditTarget: (v: DataEntryRow | null) => void;
    projectId: string;
    updateRows: (key: keyof TableRowMap, updater: DataEntryRow[] | ((previous: DataEntryRow[]) => DataEntryRow[])) => void;
    computeEmissionsForRow: (key: UploadKey, row: DataEntryRow) => Promise<Partial<DataEntryRow> | null>;
    adminDecisionOpen: AdminDecisionAction | null;
    setAdminDecisionOpen: Dispatch<SetStateAction<AdminDecisionAction | null>>;
    decisionComments: string;
    setDecisionComments: (v: string) => void;
    triggerAdminDecision: () => void;
    reopenModalOpen: boolean;
    setReopenModalOpen: (v: boolean) => void;
    activeStage: StageLabel;
    _projectName: string | null;
    reopenJustification: string;
    setReopenJustification: (v: string) => void;
    submitReopenRequest: () => void;
    submitModalOpen: boolean;
    setSubmitModalOpen: (v: boolean) => void;
    handleReportSubmission: () => void;
    isBusinessCaseStage: boolean;
    activeStageInstance: StageInstance | null;
    manageOptionsOpen: boolean;
    setManageOptionsOpen: (v: boolean) => void;
    activeReportNumber: number;
    currentReportSubOptions: ProjectOption[];
    onOptionsChange: () => Promise<void>;
    copyDataOpen: boolean;
    setCopyDataOpen: (v: boolean) => void;
    baseCaseOptions: SelectOption[];
    activeOptionId: string | null;
    onCopied: () => Promise<void>;
    periodWorkflowOpen: PeriodWorkflowAction | null;
    setPeriodWorkflowOpen: Dispatch<SetStateAction<PeriodWorkflowAction | null>>;
    activePeriod: ConstructionPeriod | null;
    handlePeriodWorkflowConfirm: (reason?: string) => Promise<void>;
}

export function DataEntryModals({
    uploadTarget, setUploadTarget, parseFile, validateUpload, onUploadSuccess,
    deleteTarget, setDeleteTarget, doDeleteRow,
    designSeedConfirmOpen, pendingDesignReportNum, reDesignSeedLoading,
    onCancelDesignSeed, onConfirmDesignSeed,
    addLargeYearOpen, addLargeYearInput, addLargeYearError,
    setAddLargeYearOpen, setAddLargeYearInput, setAddLargeYearError, handleAddLargeYear,
    copyLargeYearConfirmOpen, copyLargeYearSource, activeLargeUsersYear, largeUsersYears,
    setCopyLargeYearConfirmOpen, setCopyLargeYearSource, handleCopyLargeYear,
    deleteLargeYearConfirmOpen, setDeleteLargeYearConfirmOpen, handleDeleteLargeYear,
    concreteMixModalType, setConcreteMixModalType, concreteMixEditTarget, setConcreteMixEditTarget,
    projectId, updateRows, computeEmissionsForRow,
    adminDecisionOpen, setAdminDecisionOpen, decisionComments, setDecisionComments, triggerAdminDecision,
    reopenModalOpen, setReopenModalOpen, activeStage, _projectName,
    reopenJustification, setReopenJustification, submitReopenRequest,
    submitModalOpen, setSubmitModalOpen, handleReportSubmission,
    isBusinessCaseStage, activeStageInstance, manageOptionsOpen, setManageOptionsOpen,
    activeReportNumber, currentReportSubOptions, onOptionsChange,
    copyDataOpen, setCopyDataOpen, baseCaseOptions, activeOptionId, onCopied,
    periodWorkflowOpen, setPeriodWorkflowOpen, activePeriod, handlePeriodWorkflowConfirm,
}: DataEntryModalsProps) {
    return (
        <>
            {uploadTarget && (
                <UploadModal
                    open={!!uploadTarget}
                    onClose={() => setUploadTarget(null)}
                    parseFile={(file) => parseFile(file, uploadTarget!)}
                    validateRows={(rows) => validateUpload(rows, uploadTarget!)}
                    onSuccess={(rows) => onUploadSuccess(rows, uploadTarget!)}
                />
            )}

            <ConfirmDeleteRowModal
                open={!!deleteTarget}
                onClose={() => setDeleteTarget(null)}
                onConfirm={doDeleteRow}
            />

            {designSeedConfirmOpen && pendingDesignReportNum !== null && (
                <DesignSeedConfirmModal
                    open={designSeedConfirmOpen}
                    pendingDesignReportNum={pendingDesignReportNum}
                    reDesignSeedLoading={reDesignSeedLoading}
                    onCancel={onCancelDesignSeed}
                    onConfirm={onConfirmDesignSeed}
                />
            )}

            {addLargeYearOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-full">
                        <h3 className="text-lg font-semibold mb-4">Add modelled year</h3>
                        <input
                            type="number"
                            className="h-9 w-full border border-border-input rounded px-2 text-sm mb-2"
                            placeholder="e.g. 2050"
                            value={addLargeYearInput}
                            onChange={e => { setAddLargeYearInput(e.target.value); setAddLargeYearError(null); }}
                            onKeyDown={e => { if (e.key === "Enter") void handleAddLargeYear(); if (e.key === "Escape") { setAddLargeYearOpen(false); setAddLargeYearInput(""); setAddLargeYearError(null); } }}
                            autoFocus
                        />
                        {addLargeYearError && <p className="text-xs text-danger mb-2">{addLargeYearError}</p>}
                        <div className="flex justify-end gap-3 mt-4">
                            <button
                                type="button"
                                onClick={() => { setAddLargeYearOpen(false); setAddLargeYearInput(""); setAddLargeYearError(null); }}
                                className="px-4 py-2 text-sm cursor-pointer border cursor-pointer border-neutral-300 rounded hover:bg-neutral-100"
                            >Cancel</button>
                            <button
                                type="button"
                                onClick={() => void handleAddLargeYear()}
                                className="px-4 py-2 text-sm  cursor-pointer bg-primary text-white rounded hover:bg-primary-dark"
                            >Add</button>
                        </div>
                    </div>
                </div>
            )}

            {copyLargeYearConfirmOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-full">
                        <h3 className="text-lg font-semibold mb-2">Copy from another year</h3>
                        <p className="text-sm text-text-base mb-4">
                            Select a source year to copy data into year <strong>{activeLargeUsersYear}</strong>. This will overwrite all existing data for that year.
                        </p>
                        <select
                            className="h-9 w-full border border-border-input rounded px-2 text-sm bg-white mb-4"
                            value={copyLargeYearSource ?? ""}
                            onChange={e => setCopyLargeYearSource(e.target.value ? Number(e.target.value) : null)}
                        >
                            <option value="">Select year…</option>
                            {largeUsersYears.filter(y => y !== activeLargeUsersYear).map(y => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                        <div className="flex justify-end gap-3">
                            <button
                                type="button"
                                onClick={() => { setCopyLargeYearConfirmOpen(false); setCopyLargeYearSource(null); }}
                                className="px-4 py-2 text-sm border cursor-pointer border-neutral-300 rounded hover:bg-neutral-100"
                            >Cancel</button>
                            <button
                                type="button"
                                disabled={copyLargeYearSource === null}
                                onClick={() => void handleCopyLargeYear()}
                                className="px-4 py-2 text-sm bg-primary cursor-pointer text-white rounded hover:bg-primary-dark disabled:opacity-50"
                            >Copy</button>
                        </div>
                    </div>
                </div>
            )}

            {deleteLargeYearConfirmOpen && activeLargeUsersYear !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-full">
                        <h3 className="text-lg font-semibold mb-2">Delete modelled year {activeLargeUsersYear}?</h3>
                        <p className="text-sm text-text-base mb-6">
                            All road user, rail user, and road parameter data for year <strong>{activeLargeUsersYear}</strong> will be permanently deleted. This cannot be undone.
                        </p>
                        <div className="flex justify-end gap-3">
                            <button
                                type="button"
                                onClick={() => setDeleteLargeYearConfirmOpen(false)}
                                className="px-4 py-2 text-sm border border-neutral-300 rounded hover:bg-neutral-100 cursor-pointer"
                            >Cancel</button>
                            <button
                                type="button"
                                onClick={() => void handleDeleteLargeYear()}
                                className="px-4 py-2 text-sm bg-danger text-white rounded hover:bg-red-700 cursor-pointer"
                            >Delete</button>
                        </div>
                    </div>
                </div>
            )}

            {concreteMixModalType && projectId && (
                <ConcreteMixModal
                    projectId={projectId}
                    stageInstanceId={activeStageInstance?.id ?? ""}
                    optionId={activeOptionId}
                    modalType={concreteMixModalType}
                    onClose={() => setConcreteMixModalType(null)}
                    onCreated={(row) => {
                        updateRows("concreteRegDetailed", (prev) => [...prev, row]);
                        setConcreteMixModalType(null);
                    }}
                    calculateConcreteDetailed={(row) =>
                        computeEmissionsForRow("concreteRegDetailed", row)
                    }
                />
            )}

            {concreteMixEditTarget && projectId && (
                <ConcreteMixModal
                    projectId={projectId}
                    stageInstanceId={activeStageInstance?.id ?? ""}
                    optionId={activeOptionId}
                    modalType={concreteMixEditTarget.method as "mix_design" | "epd_pcf"}
                    editMix={concreteMixEditTarget}
                    calculateConcreteDetailed={(row) =>
                        computeEmissionsForRow("concreteRegDetailed", row)
                    }
                    onClose={() => setConcreteMixEditTarget(null)}
                    onCreated={(row) => {
                        updateRows("concreteRegDetailed", (prev) =>
                            prev.map((r) => (r.id === row.id ? { ...r, ...row } : r))
                        );
                        setConcreteMixEditTarget(null);
                    }}
                />
            )}

            <AdminDecisionModal
                open={!!adminDecisionOpen}
                adminDecisionOpen={adminDecisionOpen}
                decisionComments={decisionComments}
                onDecisionCommentsChange={setDecisionComments}
                onClose={() => setAdminDecisionOpen(null)}
                onConfirm={triggerAdminDecision}
            />

            <SimpleModal open={reopenModalOpen} title="Request to reopen report" onClose={() => setReopenModalOpen(false)}>
                <div className="text-text-base text-base mb-6">You are requesting to reopen the <strong>{activeStage}</strong> stage submission for the <strong>{_projectName}</strong>.</div>
                <div className="text-text-base text-sm mb-6">Please provide a justification so the administrator can properly evaluate your request.</div>
                <label htmlFor="justification" className="text-text-base text-base"><strong>Justification</strong> (required)</label>
                <textarea
                    id="justification"
                    className="border border-border-input w-full rounded-[var(--radius-3)] h-28 p-3 mb-8"
                    value={reopenJustification}
                    onChange={(e) => setReopenJustification(e.target.value)}
                />
                <div className="text-right mt-4">
                    <button className="px-4 py-2 rounded mr-2" onClick={() => setReopenModalOpen(false)}>Cancel</button>
                    <button className="bg-primary text-white px-4 py-2 rounded cursor-pointer disabled:opacity-60"
                        disabled={!reopenJustification.trim()}
                        onClick={submitReopenRequest}>
                        Request to reopen
                    </button>
                </div>
            </SimpleModal>

            {submitModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="bg-white rounded-lg shadow-xl p-8 max-w-lg w-full mx-4 text-text-base text-base ">
                        <h2 className="text-2xl text-text-dark mb-6">Submit for approval</h2>
                        <p className="mb-3">
                            You're about to submit your report for{" "}
                            <strong>{activeStage} stage</strong>. After submission, editing will be
                            disabled while the report is under review.
                        </p>
                        <p className="mb-6">
                            By submitting you are confirming that the submission has undergone
                            appropriate technical review and quality assurance.
                        </p>
                        <p className="mb-12">Do you want to proceed?</p>
                        <div className="flex justify-end gap-4">
                            <button
                                onClick={() => setSubmitModalOpen(false)}
                                className="px-6 py-2.5 rounded-[var(--radius-3)] text-sm  cursor-pointer font-medium hover:bg-neutral-50 transition-colors"
                            >
                                Keep editing
                            </button>
                            <button
                                onClick={handleReportSubmission}
                                className="bg-primary text-white px-6 py-2.5 cursor-pointer rounded-[var(--radius-3)] text-sm font-medium hover:bg-opacity-90 transition-colors"
                            >
                                Yes, proceed with submission
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {isBusinessCaseStage && activeStageInstance && (
                <>
                    <ManageOptionsModal
                        open={manageOptionsOpen}
                        onClose={() => setManageOptionsOpen(false)}
                        activeStage={activeStage}
                        projectId={projectId}
                        stageInstanceId={activeStageInstance.id}
                        reportNumber={activeReportNumber}
                        options={currentReportSubOptions}
                        onOptionsChange={onOptionsChange}
                    />
                    <CopyDataModal
                        open={copyDataOpen}
                        onClose={() => setCopyDataOpen(false)}
                        options={baseCaseOptions}
                        currentOptionId={activeOptionId ?? ""}
                        onCopied={onCopied}
                    />
                </>
            )}

            <PeriodWorkflowModal
                open={periodWorkflowOpen !== null}
                action={periodWorkflowOpen}
                period={activePeriod}
                onConfirm={handlePeriodWorkflowConfirm}
                onCancel={() => setPeriodWorkflowOpen(null)}
            />
        </>
    );
}
