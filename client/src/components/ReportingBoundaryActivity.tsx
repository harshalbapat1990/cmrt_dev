import React, { useMemo, useState, useEffect } from "react";
import MultiSelectDropdown, { type MSOption } from "./common/MultiSelectDropDown";
import ChipsRow, { type ChipItem } from "./common/ChipsRow";
import { SelectListbox } from "./common/Select";
import LookupsService from "../services/Lookups.service";
import { type EmissionRow } from "./common/EmissionTable";
import { downloadCsv, type CsvColumn } from "../utils/downloadCsv";
import { uploadCsv, type ParsedRow } from "../utils/uploadCsv";

/** Contractor (Recurring treated same) Activity options */
const ACTIVITY_OPTIONS: MSOption[] = [
  { label: "Construction plant/equipment", value: "Construction plant/equipment" },
  { label: "Land clearing", value: "Land clearing" },
  { label: "Materials", value: "Materials" },
  { label: "Permanent depots / facilities", value: "Permanent depots / facilities" },
  { label: "Temporary sites / camps", value: "Temporary sites / camps" },
  { label: "Vehicle fleet", value: "Vehicle fleet" },
];

export const ACTIVITY_CATEGORY_MAP: Record<string, string[]> = {
  "Construction plant/equipment": ["Fuels", "Electricity"],
  "Land clearing": ["Vegetation"],
  "Materials": ["Materials"],
  "Permanent depots / facilities": ["Fuels", "Electricity", "Gases", "Waste"],
  "Temporary sites / camps": ["Fuels", "Electricity", "Gases", "Waste"],
  "Vehicle fleet": ["Fuels", "Electricity"],
};

const RB_COLUMNS: CsvColumn[] = [
  { key: "activity", label: "Activity type" },
  { key: "category", label: "Emissions category" },
  { key: "subCategory", label: "Emissions sub-category" },
  { key: "source", label: "Emissions source" },
];

/** ---------- CSV helpers ---------- */
const normalize = (s: string) => s.trim().toLowerCase();

const matchByValueOrLabelToValue = (raw: string, options: any[]): string => {
  if (!raw) return "";
  const asIs = options.find((o) => o.value === raw)?.value;
  if (asIs) return asIs;
  const byLabel = options.find((o) => normalize(o.label) === normalize(raw))?.value;
  return byLabel || "";
};

const findLabel = (value: string, options: any[]) =>
  options.find((o) => o.value === value)?.label ?? value;

/** Convert MSOption[] -> Option[] for SelectListbox */
const toOption = (xs: MSOption[]): any[] => xs.map((x) => ({ value: x.value, label: x.label }));

/** ----- Operation panel for a selected activity type ----- */
type RBActivityOperationPanelProps = {
  activeActivity: string;
  onAddManual: (row: Omit<EmissionRow, "id" | "origin">) => void;
  onUploadParsed?: (rows: EmissionRow[]) => void;
  onClose: () => void;
  activityOptions: MSOption[];
};

const RBActivityOperationPanel: React.FC<RBActivityOperationPanelProps> = ({
  activeActivity,
  onAddManual,
  onUploadParsed,
  activityOptions,
}) => {
  const [categoryOptions, setCategoryOptions] = useState<any[]>([]);
  const [subcatOptions, setSubcatOptions] = useState<any[]>([]);
  const [sourceOptions, setSourceOptions] = useState<any[]>([]);

  const [cat, setCat] = useState("");
  const [subCat, setSubCat] = useState("");
  const [source, setSource] = useState("");

  const [loadingSubcats, setLoadingSubcats] = useState(false);
  const [loadingSources, setLoadingSources] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const allowed = ACTIVITY_CATEGORY_MAP[activeActivity] ?? [];
    setCategoryOptions(allowed.map((name) => ({ value: name, label: name })));
  }, [activeActivity]);

  const handleChangeCat = async (categoryId: string) => {
    setCat(categoryId);
    setSubCat("");
    setSource("");
    setSourceOptions([]);

    if (!categoryId) {
      setSubcatOptions([]);
      return;
    }

    try {
      setLoadingSubcats(true);
      const categoryLabel = findLabel(categoryId, categoryOptions);
      const subs = await LookupsService.fetchGrade3Subcategories(categoryLabel);
      setSubcatOptions(subs);
    } catch (e) {
      console.error(e);
      setSubcatOptions([]);
      setErrorMessage("Failed to load Emissions sub-categories.");
    } finally {
      setLoadingSubcats(false);
    }
  };

  const handleChangeSubcat = async (subcatId: string) => {
    setSubCat(subcatId);
    setSource("");

    if (!subcatId) {
      setSourceOptions([]);
      return;
    }

    try {
      setLoadingSources(true);
      const categoryLabel = findLabel(cat, categoryOptions);
      const sources = await LookupsService.fetchGrade3Sources(categoryLabel, subcatId);
      setSourceOptions(sources);
    } catch (e) {
      console.error(e);
      setSourceOptions([]);
      setErrorMessage("Failed to load Emissions sources.");
    } finally {
      setLoadingSources(false);
    }
  };

  const canAdd = Boolean(activeActivity && cat && subCat && source);

  const handleAdd = () => {
    if (!canAdd) return;

    // Push LABELS (not IDs) to table
    onAddManual({
      stageOrActivity: activeActivity,
      category: findLabel(cat, categoryOptions),
      subCategory: findLabel(subCat, subcatOptions),
      source: findLabel(source, sourceOptions),
    });

    // Clear selections for next add
    setCat("");
    setSubCat("");
    setSource("");
    setSubcatOptions([]);
    setSourceOptions([]);
    setErrorMessage(null);
  };

  const downloadTemplate = () => {
    downloadCsv(
      RB_COLUMNS,
      [], // no rows -> header-only
      "activity_emissions_template.csv",
      true, 
      true  
    );
  };


  const handleUpload: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      // 1) Parse CSV (label-driven)
      const parsed: ParsedRow[] = await uploadCsv(file, {
        columns: RB_COLUMNS, // fallback exact-match by label
        normalizeHeader: (label: string) => {
          const s = label.trim().toLowerCase();
          if (s === "activity type") return "activity";
          if (s === "emissions category") return "category";
          if (s === "emissions sub-category" || s === "emissions sub category")
            return "subCategory";
          if (s === "emissions source" || s === "source") return "source";

          // fallback exact label match from RB_COLUMNS
          const found = RB_COLUMNS.find((c) => c.label.trim().toLowerCase() === s);
          return found ? found.key : "";
        },
      });

      const activityOpts: any[] = toOption(activityOptions);
      const imported: EmissionRow[] = [];

      // 2) For each row -> resolve names to values via lookups, then push LABELS to table
      for (const obj of parsed) {
        const actRaw = String(obj.activity ?? "");
        const catRaw = String(obj.category ?? "");
        const subRaw = String(obj.subCategory ?? "");
        const srcRaw = String(obj.source ?? "");

        // Resolve activity
        const actVal = matchByValueOrLabelToValue(actRaw, activityOpts);
        const actLabel = actVal ? findLabel(actVal, activityOpts) : actRaw;

        // Resolve category -> subcat -> source (values)
        const catVal = matchByValueOrLabelToValue(catRaw, categoryOptions);
        const catLabel = catVal ? findLabel(catVal, categoryOptions) : catRaw;

        let subOptions: any[] = [];
        if (catLabel) {
          try {
            subOptions = await LookupsService.fetchGrade3Subcategories(catLabel);
          } catch {
            subOptions = [];
          }
        }
        const subVal = matchByValueOrLabelToValue(subRaw, subOptions);

        let srcOptions: any = [];
        if (catLabel && subVal) {
          try {
            srcOptions = await LookupsService.fetchGrade3Sources(catLabel, subVal);
          } catch {
            srcOptions = [];
          }
        }
        const srcVal = matchByValueOrLabelToValue(srcRaw, srcOptions);

        imported.push({
          id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          origin: "uploaded",
          stageOrActivity: actLabel || actRaw,
          category: catVal ? findLabel(catVal, categoryOptions) : catRaw,
          subCategory: subVal ? findLabel(subVal, subOptions) : subRaw,
          source: srcVal ? findLabel(srcVal, srcOptions) : srcRaw,
        });
      }

      onUploadParsed?.(imported);
      setErrorMessage(null);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(err?.message || "Failed to parse or import the uploaded file.");
    } finally {
      e.currentTarget.value = ""; // allow re-uploading the same file
    }
  };


  return (
    <div className="relative rounded-[var(--radius-3)] border border-neutral-90/10 bg-white p-4">
      <div className="mb-2 text-base text-text-dark">{activeActivity}</div>
      <div className="mb-6.25 text-xs text-text-faint">
        Select all emissions sources required to be reported under {activeActivity.toLowerCase()}.
      </div>

      {/* Actions */}
      <div className="mb-10 grid grid-cols-1 gap-2 md:grid-cols-2">
        <label className="flex w-full cursor-pointer items-center justify-center gap-2 border border-border-input bg-white px-3 py-2 text-sm hover:bg-neutral-90">
          <input type="file" accept=".csv" className="hidden" onChange={handleUpload} />
          <span className="material-symbols-rounded">upload_file</span>
          <span className="text-sm font-medium">Upload file</span>
        </label>

        <button
          type="button"
          className="flex w-full items-center justify-center gap-2 border border-border-input bg-white px-3 py-2 text-sm hover:bg-neutral-90 cursor-pointer"
          onClick={downloadTemplate}
        >
          <span className="material-symbols-rounded">download</span>
          <span className="text-sm font-medium">Download template</span>
        </button>
      </div>

      {/* Error message */}
      {errorMessage && (
        <div className="text-sm text-primary mb-4" role="alert">
          {errorMessage}
        </div>
      )}

      {/* Divider */}
      <div className="my-3 mb-8 flex items-center gap-4">
        <div className="h-px grow bg-neutral-200" />
        <div className="text-xs text-text-faint">or add manually</div>
        <div className="h-px grow bg-neutral-200" />
      </div>

      {/* Manual add (Category -> Sub-category -> Source) */}
      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="flex flex-col">
          <SelectListbox
            value={cat}
            onChange={(v: string) => handleChangeCat(v)}
            options={categoryOptions}
            label="Emissions category"
            aria-label="Emissions category"
            placeholder=""
          />
        </div>

        <div className="flex flex-col">
          <SelectListbox
            value={subCat}
            onChange={(v: string) => handleChangeSubcat(v)}
            options={subcatOptions}
            label="Emissions sub-category"
            aria-label="Emissions sub-category"
            placeholder=""
            disabled={!cat || loadingSubcats}
          />
        </div>

        <div className="flex flex-col">
          <SelectListbox
            value={source}
            onChange={(v: string) => setSource(v)}
            options={sourceOptions}
            label="Emissions source"
            aria-label="Emissions source"
            placeholder=""
            disabled={!subCat || loadingSources}
          />
        </div>
      </div>

      {/* Add action */}
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          className="rounded bg-white px-6 py-2 text-sm font-semibold cursor-pointer text-primary disabled:cursor-not-allowed disabled:opacity-50"
          onClick={handleAdd}
          disabled={!canAdd}
        >
          Add
        </button>
      </div>


    </div>
  );
};

/** ---------- Main component ---------- */
export type ReportingBoundaryActivityProps = {
  value: EmissionRow[];
  onChange: (rows: EmissionRow[]) => void;
  initialActivities?: string[];
  defaultExpanded?: boolean;
  activityOptions?: MSOption[];
  errors?: {
  required?: string;
};

};

const ReportingBoundaryActivity: React.FC<ReportingBoundaryActivityProps> = ({
  value,
  onChange,
  errors,
  initialActivities = [],
  defaultExpanded = false,
  activityOptions = ACTIVITY_OPTIONS,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [selectedActivities, setSelectedActivities] = useState<string[]>(initialActivities);
  const [activeActivity, setActiveActivity] = useState<string | null>(null);

  /** Inline edit state */
  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [draft, setDraft] = useState<{
    activityVal: string; // value from activityOptions
    categoryId: string;
    subCategoryId: string;
    sourceId: string;
  }>({ activityVal: "", categoryId: "", subCategoryId: "", sourceId: "" });

  const [categoryOptions, setCategoryOptions] = useState<any[]>([]);
  const [subcatOptions, setSubcatOptions] = useState<any[]>([]);
  const [sourceOptions, setSourceOptions] = useState<any[]>([]);

  const [loadingSubcats, setLoadingSubcats] = useState(false);
  const [loadingSources, setLoadingSources] = useState(false);

  const activityOptionsAsOption = useMemo(() => toOption(activityOptions), [activityOptions]);

  /** Complete after at least one emission added */
  const isComplete = value.length > 0;

    useEffect(() => {
    if (errors && Object.keys(errors).length > 0) {
      setExpanded(true);
    }
  }, [errors]);

  const chips: ChipItem[] = useMemo(
    () => selectedActivities.map((a) => ({ id: a, label: a })),
    [selectedActivities]
  );

  const handleActivitiesChange = (next: string[]) => {
    setSelectedActivities(next);
    if (activeActivity && !next.includes(activeActivity)) setActiveActivity(null);
  };

  const addManualRow = (row: Omit<EmissionRow, "id" | "origin">) => {
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    onChange([...value, { ...row, id, origin: "manual" }]);
  };

  const addUploadedRows = (rows: EmissionRow[]) => {
    onChange([...value, ...rows]);
  };

  /** ----- Table: edit/delete ----- */
  const startEdit = async (row: EmissionRow) => {
    setEditingRowId(row.id);

    const allowed = ACTIVITY_CATEGORY_MAP[row.stageOrActivity] ?? [];
    const localCatOptions = allowed.map((name) => ({ value: name, label: name }));
    setCategoryOptions(localCatOptions);

    // Resolve ACTIVITY value from label
    const activityVal =
      activityOptionsAsOption.find((o) => normalize(o.label) === normalize(row.stageOrActivity))?.value ||
      row.stageOrActivity;

    // Resolve CATEGORY value from label
    const categoryId =
      localCatOptions.find((o) => normalize(o.label) === normalize(row.category))?.value || "";

    // Load subcategories from BGM grade 3
    let subOptions: any[] = [];
    try {
      setLoadingSubcats(true);
      subOptions = await LookupsService.fetchGrade3Subcategories(row.category);
      setSubcatOptions(subOptions);
    } finally {
      setLoadingSubcats(false);
    }

    // BGM options use name as value, so the resolved ID is the name itself
    const subCategoryId = row.subCategory;

    // Load sources from BGM grade 3
    let srcOptions: any[] = [];
    if (row.subCategory) {
      try {
        setLoadingSources(true);
        srcOptions = await LookupsService.fetchGrade3Sources(row.category, row.subCategory);
        setSourceOptions(srcOptions);
      } finally {
        setLoadingSources(false);
      }
    } else {
      setSourceOptions([]);
    }

    // BGM options use name as value, so the resolved ID is the name itself
    const sourceId = row.source;

    setDraft({ activityVal, categoryId, subCategoryId, sourceId });
  };

  const cancelEdit = () => {
    setEditingRowId(null);
    setDraft({ activityVal: "", categoryId: "", subCategoryId: "", sourceId: "" });
    setSubcatOptions([]);
    setSourceOptions([]);
  };

  const saveEdit = () => {
    if (!editingRowId) return;

    const updated = value.map((r) =>
      r.id !== editingRowId
        ? r
        : {
          ...r,
          // stageOrActivity: r.stageOrActivity,
          category: findLabel(draft.categoryId, categoryOptions) || r.category,
          subCategory: findLabel(draft.subCategoryId, subcatOptions) || r.subCategory,
          source: findLabel(draft.sourceId, sourceOptions) || r.source,
        }
    );
    onChange(updated);
    cancelEdit();
  };

  const removeRow = (rowId: string) => {
    onChange(value.filter((r) => r.id !== rowId));
    if (editingRowId === rowId) cancelEdit();
  };

  /** Cascading within the edit row */
  // const onEditActivityChange = (v: string) => setDraft((d) => ({ ...d, activityVal: v }));
  const onEditCategoryChange = async (categoryId: string) => {
    setDraft((d) => ({ ...d, categoryId, subCategoryId: "", sourceId: "" }));
    setSourceOptions([]);
    if (!categoryId) {
      setSubcatOptions([]);
      return;
    }
    try {
      setLoadingSubcats(true);
      const categoryLabel = findLabel(categoryId, categoryOptions);
      const subs = await LookupsService.fetchGrade3Subcategories(categoryLabel);
      setSubcatOptions(subs);
    } finally {
      setLoadingSubcats(false);
    }
  };
  const onEditSubcategoryChange = async (subId: string) => {
    setDraft((d) => ({ ...d, subCategoryId: subId, sourceId: "" }));
    if (!subId) {
      setSourceOptions([]);
      return;
    }
    try {
      setLoadingSources(true);
      const categoryLabel = findLabel(draft.categoryId, categoryOptions);
      const srcs = await LookupsService.fetchGrade3Sources(categoryLabel, subId);
      setSourceOptions(srcs);
    } finally {
      setLoadingSources(false);
    }
  };
  const onEditSourceChange = (srcId: string) => setDraft((d) => ({ ...d, sourceId: srcId }));

  /** Visible table when chip active or rows exist */
  const shouldShowTable = Boolean(activeActivity) || value.length > 0;

  // 3‑state icon logic (same as Small)
  const getStatusIcon = () => {
    if (isComplete) return "check_circle";
    if (expanded) return "radio_button_partial";
    return "radio_button_unchecked";
  };

  return (
    <div className="border-t border-neutral-200 p-4">
      {/* Header */}
      <button
  type="button"
  onClick={() => setExpanded((v) => !v)}
  className="mb-8 w-full flex items-center justify-between gap-2 text-left cursor-pointer"
  aria-expanded={expanded}
  aria-controls="reporting-boundary-activity-panel"
  title={expanded ? "Collapse" : "Expand"}
>
  <div className="flex min-w-0 items-center text-text-dark">
    <span
      className="material-symbols-rounded mr-2 shrink-0 text-lg"
      aria-hidden="true"
    >
      {getStatusIcon()}
    </span>

    <span className="truncate">
      Reporting boundary
    </span>
  </div>

  <span className="material-symbols-rounded shrink-0">
    {expanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
  </span>
</button>


      {expanded && (
        <div id="reporting-boundary-activity-panel" className="space-y-4 mb-7 rounded-md bg-bg-content">
          {/* Multi-select Activities */}
          <MultiSelectDropdown
            label="Activity types"
            options={activityOptions}
            selected={selectedActivities}
            onChange={handleActivitiesChange}
            placeholder="Select all that apply"
            withSearch={false}
            closeOnSelect={false}
            className="mb-10"
          />

          {/* Chips */}
          {selectedActivities.length > 0 && (
            <div>
              <div className="mb-2 mt-1 text-text-base text-text-dark">
                <div>Selected activity types</div>
                <div className="mt-1 text-sm text-text-faint">
                  Choose an activity type to start adding emissions sources
                </div>
              </div>
              <ChipsRow
                items={chips}
                activeId={activeActivity}
                onActivate={setActiveActivity}
                onRemove={(id) => handleActivitiesChange(selectedActivities.filter((x) => x !== id))}
                wrap={false}
                align="left"
                size="md"
                className="mt-4"
              />
            </div>
          )}

          {/* Operation panel */}
          {activeActivity && selectedActivities.includes(activeActivity) && (
            <RBActivityOperationPanel
              activeActivity={activeActivity}
              onAddManual={addManualRow}
              onUploadParsed={addUploadedRows}
              onClose={() => setActiveActivity(null)}
              activityOptions={activityOptions}
            />
          )}

          {/* Table — with inline edit/delete */}
          {shouldShowTable && (
            <div className="mt-8">
              <div className="mb-2 text-base text-text-dark">Emissions sources</div>

              {/* Table header */}
              <div className="grid grid-cols-5 gap-0 border-collapse border border-light-grey p-4 bg-neutral-90 border-b-0 rounded-[var(--radius-3)] rounded-b-none text-base text-text-dark">
                {[
                  "Activity type",
                  "Emissions category",
                  "Emissions sub-category",
                  "Emissions source",
                ].map((label, i) => (
                  <div
                    key={label}
                    className={[
                      "h-12 flex items-center text-sm font-medium",
                      i !== 0 ? "border-l border-neutral-90 pl-4" : "",
                    ].join(" ")}
                  >
                    {label}
                  </div>
                ))}
              </div>

              {/* Table body */}
              <div>
                {value.map((row) => {
                  const isEditing = editingRowId === row.id;

                  return (
                    <div
                      key={row.id}
                      className={[
                        "grid grid-cols-5 gap-0 border-collapse border-b border-light-grey bg-white last:rounded-b-sm",
                        isEditing ? "p-4" : "py-3 px-2",
                      ].join(" ")}
                    >
                      {/* Activity type */}
                      <div
                        className={!isEditing ? "min-h-10 h-10 flex items-center text-sm text-text-dark bg-white cursor-pointer" : ""}
                        onDoubleClick={() => !isEditing && startEdit(row)}
                        role={!isEditing ? "button" : undefined}
                        tabIndex={!isEditing ? 0 : -1}
                        title={!isEditing ? "Double-click to edit" : undefined}
                        onKeyDown={(e) => {
                          if (!isEditing && e.key === "Enter") startEdit(row);
                        }}
                      >
                        {row.stageOrActivity}
                      </div>

                      {/* Category */}
                      <div
                        className={!isEditing ? "ml-4 min-h-10 h-10 flex items-center text-sm text-text-dark bg-white cursor-pointer" : "ml-4"}
                        onDoubleClick={() => !isEditing && startEdit(row)}
                        role={!isEditing ? "button" : undefined}
                        tabIndex={!isEditing ? 0 : -1}
                        title={!isEditing ? "Double-click to edit" : undefined}
                        onKeyDown={(e) => {
                          if (!isEditing && e.key === "Enter") startEdit(row);
                        }}
                      >
                        {isEditing ? (
                          <SelectListbox
                            value={draft.categoryId}
                            onChange={(v: string) => onEditCategoryChange(v)}
                            options={categoryOptions}
                            aria-label="Emissions category"
                            placeholder=""
                            className="w-full h-10 px-3 border border-border-input rounded-[var(--radius-3)] text-sm text-text-dark bg-white focus:outline-none focus:ring-1 focus:ring-text-dark focus:border-transparent"
                          />
                        ) : (
                          row.category
                        )}
                      </div>

                      {/* Sub-category */}
                      <div
                        className={!isEditing ? "ml-4 min-h-10 h-10 flex items-center text-sm text-text-dark bg-white cursor-pointer" : "ml-4"}
                        onDoubleClick={() => !isEditing && startEdit(row)}
                        role={!isEditing ? "button" : undefined}
                        tabIndex={!isEditing ? 0 : -1}
                        title={!isEditing ? "Double-click to edit" : undefined}
                        onKeyDown={(e) => {
                          if (!isEditing && e.key === "Enter") startEdit(row);
                        }}
                      >
                        {isEditing ? (
                          <SelectListbox
                            value={draft.subCategoryId}
                            onChange={(v: string) => onEditSubcategoryChange(v)}
                            options={subcatOptions}
                            aria-label="Emissions sub-category"
                            placeholder=""
                            disabled={!draft.categoryId || loadingSubcats}
                            className="w-full h-10 px-3 border border-border-input rounded-[var(--radius-3)] text-sm text-text-dark bg-white focus:outline-none focus:ring-1 focus:ring-text-dark focus:border-transparent"
                          />
                        ) : (
                          row.subCategory
                        )}
                      </div>

                      {/* Source */}
                      <div
                        className={!isEditing ? "ml-4 min-h-10 h-10 flex items-center text-sm text-text-dark bg-white cursor-pointer" : "ml-4"}
                        onDoubleClick={() => !isEditing && startEdit(row)}
                        role={!isEditing ? "button" : undefined}
                        tabIndex={!isEditing ? 0 : -1}
                        title={!isEditing ? "Double-click to edit" : undefined}
                        onKeyDown={(e) => {
                          if (!isEditing && e.key === "Enter") startEdit(row);
                        }}
                      >
                        {isEditing ? (
                          <SelectListbox
                            value={draft.sourceId}
                            onChange={(v: string) => onEditSourceChange(v)}
                            options={sourceOptions}
                            aria-label="Emissions source"
                            placeholder=""
                            disabled={!draft.subCategoryId || loadingSources}
                            className="w-full h-10 px-3 border border-border-input rounded-[var(--radius-3)] text-sm text-text-dark bg-white focus:outline-none focus:ring-1 focus:ring-text-dark focus:border-transparent"
                          />
                        ) : (
                          row.source
                        )}
                      </div>

                      {/* Actions */}
                      <div className="ml-4 flex items-center gap-3">
                        {isEditing ? (
                          <>
                            <button
                              type="button"
                              className="material-symbols-rounded text-success hover:opacity-80 cursor-pointer"
                              aria-label="Save"
                              title="Save"
                              onClick={saveEdit}
                            >
                              <span className="material-symbols-rounded text-success">
                                check
                              </span>
                            </button>
                            <button
                              type="button"
                              className="material-symbols-rounded text-primary hover:opacity-80 cursor-pointer"
                              aria-label="Cancel"
                              title="Cancel"
                              onClick={cancelEdit}
                            >
                              <span className="material-symbols-rounded text-text-dark">
                                close
                              </span>
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              type="button"
                              className="inline-flex items-center justify-center rounded-[var(--radius-3)] p-1.5 hover:bg-neutral-95 cursor-pointer"
                              aria-label="Edit row"
                              title="Edit row"
                              onClick={() => startEdit(row)}
                            >
                              <span className="material-symbols-rounded text-text-dark">edit</span>
                            </button>

                            {/* Delete */}
                            <button
                              type="button"
                              className="inline-flex items-center justify-center rounded-[var(--radius-3)] p-1.5 hover:bg-neutral-95 cursor-pointer"
                              aria-label="Delete row"
                              title="Delete row"
                              onClick={() => removeRow(row.id)}
                            >
                              <span className="material-symbols-rounded text-primary">delete</span>
                            </button>

                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ReportingBoundaryActivity;
