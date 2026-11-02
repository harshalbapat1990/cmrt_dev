import { useCallback, useState } from "react";

export function useDesignSeedWorkflow() {
  const [designReportNum, setDesignReportNum] = useState(1);
  const [pendingDesignReportNum, setPendingDesignReportNum] = useState<number | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);

  const requestReportChange = useCallback((reportNumber: number) => {
    setPendingDesignReportNum(reportNumber);
    setConfirmOpen(true);
  }, []);

  const cancelReportChange = useCallback(() => {
    setConfirmOpen(false);
    setPendingDesignReportNum(null);
  }, []);

  const confirmReportChange = useCallback(async (
    seedPeriodsFromDesign: (periodIds: string[]) => Promise<void>,
    constructionPeriodIds: string[],
  ) => {
    if (pendingDesignReportNum === null) return;
    const reportNumber = pendingDesignReportNum;
    setConfirmOpen(false);
    setDesignReportNum(reportNumber);
    setPendingDesignReportNum(null);
    setIsSeeding(true);
    try {
      await seedPeriodsFromDesign(constructionPeriodIds);
    } finally {
      setIsSeeding(false);
    }
  }, [pendingDesignReportNum]);

  return {
    designReportNum,
    pendingDesignReportNum,
    confirmOpen,
    isSeeding,
    requestReportChange,
    cancelReportChange,
    confirmReportChange,
  };
}
