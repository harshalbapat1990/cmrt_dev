interface DatasetBulkBarProps {
  onDownload: () => void;
  onDownloadTemplate: () => void;
  onUpload?: () => void;
  canEdit?: boolean;
  loading?: boolean;
}

export default function DatasetBulkBar({
  onDownload,
  onDownloadTemplate,
  onUpload,
  canEdit,
  loading,
}: DatasetBulkBarProps) {
  const btnBase =
    'flex items-center gap-1 rounded border border-neutral-80 bg-white px-2.5 py-1 text-xs font-medium text-text-base hover:bg-neutral-98 disabled:opacity-40 whitespace-nowrap';

  return (
    <div className="flex items-center gap-2">
      <button type="button" className={btnBase} onClick={onDownload} disabled={loading} title="Download current data as CSV">
        <span className="cursor-pointer material-symbols-rounded text-[14px] leading-none">download</span>
        Download
      </button>
      <button type="button" className={btnBase} onClick={onDownloadTemplate} disabled={loading} title="Download blank CSV template">
        <span className="cursor-pointer material-symbols-rounded text-[14px] leading-none">draft</span>
        Template
      </button>
      {canEdit && onUpload && (
        <button type="button" className={btnBase} onClick={onUpload} disabled={loading} title="Upload CSV to upsert rows">
          <span className="cursor-pointer material-symbols-rounded text-[14px] leading-none">upload</span>
          Upload
        </button>
      )}
    </div>
  );
}
