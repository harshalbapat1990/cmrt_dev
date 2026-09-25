import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
// import LeftNavigation from "../../components/LeftNavigation";
import ReportData from "../../components/ReportData";
import { getNextMonthLabel, getMonthLabelFromDate } from "../../utils/date";
import type { Report, ReportStatus } from "../../types/reports";
import http from "@/http";
import { monthLabelToKey } from "../../utils/utils";
import { useProjectStageAccess } from "@/customHooks/useProjectStageAccess";

const STORAGE_KEYS = {
  reports: "monthly.reports",
  selectedReportId: "monthly.selectedReportId",
} as const;

const safeParse = <T,>(raw: string | null): T | null => {
  if (!raw || raw === "undefined" || raw === "null") return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
};

const createInitialReport = (): Report => ({
  id: 1,
  month: getMonthLabelFromDate(new Date()),
  status: "Not Started",
});

const MonthlyReport = () => {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("projectId") ?? "";
  const {
    getAccess,
    loading: stageAccessLoading,
    error: stageAccessError,
  } = useProjectStageAccess(projectId);

  const [stageInstanceId, setStageInstanceId] = useState<string>("");
  const [submissionPeriodId, setSubmissionPeriodId] = useState<string>("");

  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);

  // Load from storage on mount 
  useEffect(() => {
    if (typeof window === "undefined") return;

    const storedReports = safeParse<Report[]>(
      window.sessionStorage.getItem(STORAGE_KEYS.reports)
    );
    const storedSelectedIdRaw = window.sessionStorage.getItem(
      STORAGE_KEYS.selectedReportId
    );

    if (!Array.isArray(storedReports) || storedReports.length === 0) {
      const initial = createInitialReport();
      setReports([initial]);
      setSelectedReportId(initial.id);
      window.sessionStorage.setItem(STORAGE_KEYS.reports, JSON.stringify([initial]));
      window.sessionStorage.setItem(STORAGE_KEYS.selectedReportId, String(initial.id));
      return;
    }

    setReports(storedReports);

    if (storedSelectedIdRaw) {
      const idNum = Number(storedSelectedIdRaw);
      const exists = storedReports.some((r) => r.id === idNum);
      setSelectedReportId(exists ? idNum : storedReports[storedReports.length - 1].id);
    } else {
      setSelectedReportId(storedReports[storedReports.length - 1].id);
    }
  }, []);

  const selectedReport: Report | null = useMemo(() => {
    if (!reports.length) return null;
    return (
      reports.find((r) => r.id === selectedReportId) ?? reports[reports.length - 1]
    );
  }, [reports, selectedReportId]);

  useEffect(() => {
    if (!projectId || stageAccessLoading || stageAccessError) return;
    (async () => {
      try {
        const res = await http.get(`/api/project-stage-instances?project_id=${projectId}&limit=50`);
        const instances: any[] = Array.isArray(res.data) ? res.data : [];
        const recurring = instances.find((si: any) => si.stage === "RECURRING");
        if (recurring && getAccess(recurring.id) !== "NONE") {
          setStageInstanceId(recurring.id);
        } else {
          setStageInstanceId("");
        }
      } catch (err) {
        console.error("Failed to load stage instances:", err);
      }
    })();
  }, [projectId, stageAccessLoading, stageAccessError, getAccess]);

  const recurringAccess = getAccess(stageInstanceId);
  const canEditRecurringStage = recurringAccess === "EDIT" || recurringAccess === "ADMIN";
  const canAdminRecurringStage = recurringAccess === "ADMIN";

  useEffect(() => {
    if (!projectId || !stageInstanceId || !selectedReport || !canEditRecurringStage) return;
    const periodLabel = selectedReport.month; // e.g. "January 2026"
    const ym = monthLabelToKey(periodLabel); // "2026-01"
    if (!ym) return;

    const [y, m] = ym.split("-").map(Number);
    const startDate = new Date(Date.UTC(y, m - 1, 1));
    const endDate = new Date(Date.UTC(y, m, 0)); // last day of month
    const fmt = (d: Date) => d.toISOString().slice(0, 10);

    (async () => {
      try {
        const res = await http.post("/api/project-submissions/get-or-create", {
          project_id: projectId,
          stage_instance_id: stageInstanceId,
          period_label: periodLabel,
          frequency: "MONTHLY",
          period_start_date: fmt(startDate),
          period_end_date: fmt(endDate),
        });
        setSubmissionPeriodId(res.data.id ?? "");
      } catch (err) {
        console.error("Failed to get/create submission period:", err);
      }
    })();
  }, [projectId, stageInstanceId, selectedReport, canEditRecurringStage]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.sessionStorage.setItem(STORAGE_KEYS.reports, JSON.stringify(reports));
  }, [reports]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (selectedReportId !== null) {
      window.sessionStorage.setItem(
        STORAGE_KEYS.selectedReportId,
        String(selectedReportId)
      );
    }
  }, [selectedReportId]);

  

  const isEmptyReport = selectedReport?.status === "Not Started";

  // const onSelectReport = useCallback((id: number | null) => {
  //   setSelectedReportId(id);
  // }, []);

  const updateSelectedReportStatus = useCallback(
    (status: ReportStatus) => {
      if (!selectedReport) return;
      setReports((prev) =>
        prev.map((r) => (r.id === selectedReport.id ? { ...r, status } : r))
      );
    },
    [selectedReport]
  );

  const showReportData = useCallback(() => {
    if (!canEditRecurringStage) return;
    updateSelectedReportStatus("In Progress");
  }, [canEditRecurringStage, updateSelectedReportStatus]);

  const handleSubmit = useCallback(() => {
    if (!canEditRecurringStage) return;
    updateSelectedReportStatus("Awaiting approval");
  }, [canEditRecurringStage, updateSelectedReportStatus]);

  const handleApprove = useCallback(
    (carbonValue: number) => {
      if (!canAdminRecurringStage || selectedReportId == null) return;

      setReports((prev) => {
        const current = prev.find((r) => r.id === selectedReportId);
        if (!current) return prev;

        const nextLabel = getNextMonthLabel(current.month);

        // Mark current as Approved with carbonValue
        let updated = prev.map((r) =>
          r.id === selectedReportId
            ? ({ ...r, status: "Approved" as ReportStatus, carbonValue } as Report)
            : r
        );

        // Ensure "next month" report exists; if not, create it
        const existingNext = updated.find((r) => r.month === nextLabel);
        if (!existingNext) {
          const maxId = updated.reduce((m, r) => (r.id > m ? r.id : m), 0);
          const nextId = maxId + 1;
          const newReport: Report = {
            id: nextId,
            month: nextLabel,
            status: "Not Started",
          };
          updated = [...updated, newReport];
          setSelectedReportId(nextId);
        } else {
          setSelectedReportId(existingNext.id);
        }

        return updated;
      });
    },
    [canAdminRecurringStage, selectedReportId]
  );

  if (!reports.length) {
    return (
      <div className="flex items-center justify-center h-screen text-text-base">
        Initializing reports...
      </div>
    );
  }

  if (stageAccessLoading) {
    return (
      <div className="flex items-center justify-center h-screen text-text-base">
        Checking stage access…
      </div>
    );
  }

  if (stageAccessError || !stageInstanceId) {
    return (
      <div className="flex h-screen items-center justify-center bg-bg-content">
        <div className="rounded border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h2 className="text-lg font-medium text-slate-800">No stage access</h2>
          <p className="mt-2 text-sm text-slate-500">
            You do not have access to the recurring reporting stage in this project.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <div className="shrink-0">
        {/* <LeftNavigation
          reports={reports}
          status={selectedReport?.status ?? ""}
          selectedReportId={selectedReport?.id ?? null}
          onSelectReport={onSelectReport}
        /> */}
      </div>

      <div className="flex-1 bg-bg-content">
        {!selectedReport ? (
          <div className="flex items-center justify-center h-full text-text-base">
            Loading selected report ...
          </div>
        ) : isEmptyReport ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-3xl text-text-dark font-light pb-3">No data yet</div>
            <div className="text-base text-text-base pb-6">
              Begin by entering data for {selectedReport.month}
            </div>
            {canEditRecurringStage && (
              <button
                className="bg-primary px-4 py-2 rounded-[var(--radius-3)] border border-primary cursor-pointer text-white font-medium text-sm"
                onClick={showReportData}
              >
                Enter data
              </button>
            )}
          </div>
        ) : (
          <ReportData
            key={selectedReport.id}
            currentReport={selectedReport.month}
            onSubmit={handleSubmit}
            onApprove={handleApprove}
            reportStatus={selectedReport.status as ReportStatus}
            reportId={selectedReport.id}
            projectId={projectId}
            stageInstanceId={stageInstanceId}
            submissionPeriodId={submissionPeriodId}
            canEditStage={canEditRecurringStage}
            canAdminStage={canAdminRecurringStage}
          />
        )}
      </div>
    </div>
  );
};

export default MonthlyReport;