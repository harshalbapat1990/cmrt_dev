export type Report = {
  id: number;
  status: string;
  month: string;
  carbonValue?: number;
  // Add other fields as needed
};

export type ReportStatus = 'Not Started' | 'In Progress' | 'Awaiting approval' | 'Approved';

export type ConstructionPeriodStatus =
  | 'in_progress'
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'reopen_requested';

export interface ConstructionPeriod {
  id: string;
  project_id: string;
  stage_instance_id: string | null;
  frequency: string;
  period_label: string;
  period_start_date: string;
  period_end_date: string;
  due_date: string | null;
  status: ConstructionPeriodStatus;
  submitted_by: string | null;
  submitted_at: string | null;
  decision_by: string | null;
  decision_at: string | null;
  rejection_reason: string | null;
  reopen_requested_by: string | null;
  reopen_requested_at: string | null;
  reopen_reason: string | null;
  exec_summary?: string | null;
  exec_summary_author?: string | null;
  exec_summary_date?: string | null;
  created_on: string | null;
  updated_on: string | null;
  period_emissions_tco2e: string | null;
  previous_period_emissions_tco2e: string | null;
  all_periods_emissions_tco2e: string | null;
}

export type SubStageGroup = {
  header: string;               // non-clickable group label
  childrenValues: string[];     // values from the flat subStages that should appear under this header
};


export type LeftNavigationProps = {
  reports?: Report[];
  status?: string;
  onSelectReport?: (month: string) => void;
  selectedReportId?: string | null;
  stageType?: string;
  stages?: any;
  constructionWindow?: { startDate: string, endDate: string } | null;
  onSelectStage?: (stage: string) => void;
  activeSubStage?: string | null;
  onSelectSubStage?: (subStage: string) => void;
  activeChildSubStage?: string | null;
  onSelectChildSubStage?: (child: string) => void;
  subStages?: any;
  groups?: SubStageGroup[];
  reportFrequency?: string;
  firstSubmissionMonth?: string | null;
  constructionReportStates?: { month: string; status: string }[];
  constructionPeriods?: ConstructionPeriod[];
  projectName?: string;
  programName?: string;
  activeStageInstance?:any;
  activeReportNumber?: number;
  /** Effective ADMIN access for the currently selected project stage. */
  isStageAdmin?: boolean;
  // Mitigations tab support (only meaningful for Design and Construction stages)
  showMitigations?: boolean;
  onSelectMitigations?: () => void;
  /** When false, the Mitigations sidebar entry is hidden (e.g. non-LARGE projects). */
  mitigationsTabEnabled?: boolean;
showCompleteness?: boolean;
onSelectCompleteness?: () => void;
completenessTabEnabled?: boolean;

  hasResubmissionAudit?: boolean;
  onViewResubmissionAudit?: () => void;
};


export type Row = {
  id: string;
  apiId?: string;
  isNew?: boolean;
  isFromUpload?: boolean;
  subCategory: string; // ID
  source: string;      // ID
  unit: string;        // ID
  dataQuality: string;
  quantity: number | null;
  emissions: string;   // keep as string for fixed 2-decimal display
  notes?: string;
  notes_author?: string | null;
  notes_date?: string | null;
};

export type ReportDataProps = {
  reportId: number;
  currentReport: string;  // e.g., "January 2026"
  reportStatus: ReportStatus;
  projectId: string;
  stageInstanceId: string;
  submissionPeriodId: string;
  onSubmit: () => void;
  onApprove: (carbonValue: number) => void;
  canEditStage: boolean;
  canAdminStage: boolean;
};
