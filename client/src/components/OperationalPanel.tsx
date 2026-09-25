import React, { useRef, useState } from "react";
import type {Option , OperationPanelProps} from "../types/addnewproject";

const OperationPanel: React.FC<OperationPanelProps> = ({
  title,
  onClose,
  onUploadFile,
  onDownloadTemplate,
  accept = ".csv,.xlsx",
  onAdd,
  categoryOptions,
  subCategoryOptions,
  sourceOptions,
  defaultCategory = "",
  defaultSubCategory = "",
  defaultSource = "",
  disabled = false,
  className,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [fileName, setFileName] = useState<string>("");

  const [category, setCategory] = useState<string>(defaultCategory);
  const [subCategory, setSubCategory] = useState<string>(defaultSubCategory);
  const [source, setSource] = useState<string>(defaultSource);

  const canAdd = category.trim() !== "" && subCategory.trim() !== "" && source.trim() !== "";

  const triggerFileDialog = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    onUploadFile?.(file);
    // If you want to allow re-upload of same file name, reset input value:
    e.currentTarget.value = "";
  };

  const handleAdd = () => {
    if (!canAdd || disabled) return;
    onAdd({ category: category.trim(), subCategory: subCategory.trim(), source: source.trim() });
    // reset only the inputs (keep uploaded file name as is)
    setCategory("");
    setSubCategory("");
    setSource("");
  };

  const InputOrSelect: React.FC<{
    label: string;
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
    options?: Option[];
    id?: string;
  }> = ({ label, value, onChange, placeholder, options, id }) => {
    return (
      <div className="flex flex-col">
        <label className="mb-1 text-text-base text-sm">{label}</label>
        {options && options.length > 0 ? (
          <select
            id={id}
            disabled={disabled}
            className="h-10 rounded-[var(--radius-3)] border border-border-input bg-white px-3 text-sm text-text-dark focus:outline-none focus:ring-1"
            value={value}
            onChange={(e) => onChange(e.target.value)}
          >
            <option value="">{placeholder ?? "Select..."}</option>
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            id={id}
            type="text"
            disabled={disabled}
            className="h-10 rounded-[var(--radius-3)] border border-border-input bg-white px-3 text-sm text-text-dark focus:outline-none focus:ring-1"
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange(e.target.value)}
          />
        )}
      </div>
    );
  };

  return (
    <div
      className={[
        "relative rounded-md border border-neutral-300 bg-white p-4",
        disabled ? "opacity-60" : "",
        className ?? "",
      ].join(" ")}
    >
      {/* Header with title + close (X) */}
      <div className="mb-3 flex items-center justify-between">
        <div className="text-[15px] font-medium text-[#48413F]">{title}</div>
        <button
          type="button"
          aria-label="Close"
          className="rounded p-1 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 cursor-pointer"
          onClick={onClose}
          disabled={disabled}
        >
          ✕
        </button>
      </div>

      {/* Upload & Template */}
      <div className="rounded-md border border-neutral-200 bg-neutral-50 p-3">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={handleFileChange}
            aria-hidden="true"
            tabIndex={-1}
          />
          <button
            type="button"
            onClick={triggerFileDialog}
            disabled={disabled}
            className="inline-flex items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-[#48413F] hover:bg-neutral-100 cursor-pointer"
          >
            Upload file
          </button>

          <button
            type="button"
            onClick={onDownloadTemplate}
            disabled={disabled}
            className="inline-flex items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-[#48413F] hover:bg-neutral-100 cursor-pointer"
          >
            Download template
          </button>

          {/* Selected file name */}
          {fileName && (
            <span className="truncate text-sm text-neutral-600">Selected: {fileName}</span>
          )}
        </div>

        {/* Divider with "or alternatively" */}
        <div className="my-3 flex items-center gap-3">
          <div className="h-px flex-1 bg-neutral-200" />
          <span className="text-xs text-neutral-500">or alternatively</span>
          <div className="h-px flex-1 bg-neutral-200" />
        </div>

        {/* Manual Add */}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <InputOrSelect
            label="Emissions category"
            value={category}
            onChange={setCategory}
            placeholder="Select category"
            options={categoryOptions}
            id="rb-category"
          />
          <InputOrSelect
            label="Emissions sub-category"
            value={subCategory}
            onChange={setSubCategory}
            placeholder="Select sub-category"
            options={subCategoryOptions}
            id="rb-subcategory"
          />
          <InputOrSelect
            label="Emissions source"
            value={source}
            onChange={setSource}
            placeholder="Enter or select source"
            options={sourceOptions}
            id="rb-source"
          />

          <div className="flex items-end">
            <button
              type="button"
              onClick={handleAdd}
              disabled={!canAdd || disabled}
              className={[
                "h-10 w-full rounded-[var(--radius-3)] px-4 text-sm font-semibold cursor-pointer",
                canAdd && !disabled
                  ? "bg-[#48413F] text-white hover:brightness-95"
                  : "cursor-not-allowed bg-neutral-200 text-neutral-500",
              ].join(" ")}
            >
              Add
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OperationPanel;
``