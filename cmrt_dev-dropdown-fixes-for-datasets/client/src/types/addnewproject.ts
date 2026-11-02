export type StageValue = "business" | "design" | "construction";
export type SubmissionMap = Record<StageValue, string>;

export type FormErrors = {
  stage?: string | null;
  submissions?: string | null;
  frequency?: string | null;
  period?: string | null;
};
export type Option = { label: string; value: string };

export type OperationPanelProps = {
  /** Header title (e.g., "Operations", "Vehicle Fleet") */
  title: string;

  /** Close/clear the active stage/activity */
  onClose: () => void;

  /** Upload & Template */
  onUploadFile?: (file: File) => void;
  onDownloadTemplate: () => void;
  accept?: string; // e.g., ".csv,.xlsx"

  /** Manual add callback */
  onAdd: (row: {
    category: string;
    subCategory: string;
    source: string;
  }) => void;

  /** When options are provided we render <select>, else <input type="text"> */
  categoryOptions?: Option[];
  subCategoryOptions?: Option[];
  sourceOptions?: Option[];

  /** Optional default values (if you want to prefill) */
  defaultCategory?: string;
  defaultSubCategory?: string;
  defaultSource?: string;

  /** Disable entire panel (optional) */
  disabled?: boolean;

  /** ClassName passthrough */
  className?: string;
};