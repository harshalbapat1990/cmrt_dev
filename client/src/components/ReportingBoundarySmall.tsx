import React, { useMemo, useState, useEffect } from "react";
import MultiSelectDropdown from "./common/MultiSelectDropDown"; // keep your exact casing
import ChipsRow, { type ChipItem } from "./common/ChipsRow";
import EmissionTable, { type EmissionRow } from "./common/EmissionTable";
import LookupsService from "../services/Lookups.service";
import { SelectListbox } from "./common/Select";
import { downloadCsv, type CsvColumn } from "../utils/downloadCsv";
import http from "@/http";
import { UploadModal } from "../pages/dummy-table/UploadModal";
import { parseFileToRows } from "../utils/parseFileToRows";
import { validateRows } from "../utils/ValidateRows";
import { rbConstructionUploadConfig } from "@/data/rbConstructionConfig";
import { rbOperationsUploadConfig } from "@/data/rbOperationsConfig";
import { rbMaintenanceUploadConfig } from "@/data/rbMaintenanceConfig";
/** Lifecycle options in dropdown (kept same UI) */
const LIFECYCLE_OPTIONS: any[] = [
  { label: "Construction", value: "Construction" },
  { label: "Operations", value: "Operations" },
  { label: "Maintenance", value: "Maintenance" },
];

// Template headers (match exactly what you show/download)
const RB_COLUMNS: CsvColumn[] = [
  { key: "category", label: "Emissions category" },
  { key: "subCategory", label: "Emissions sub-category" },
  { key: "source", label: "Emissions source" },
];

const RB_OPERATIONS_COLUMNS: CsvColumn[] = [
  { key: "group", label: "Group" },
  { key: "item", label: "Item" },
];

const RB_MAINTENANCE_COLUMNS: CsvColumn[] = [
  { key: "activityType", label: "Activity type" },
  { key: "item", label: "Item" },
];

/** ---- RBOperationPanel ---- */
type RBOperationPanelProps = {
  activeStage: string;
  onAddManual: (row: Omit<EmissionRow, "id" | "origin">) => void;
  onUploadParsed?: (rows: EmissionRow[]) => void;
  onClose: () => void;
};

const RBOperationPanel: React.FC<RBOperationPanelProps> = ({
  activeStage,
  onAddManual,
  onUploadParsed,
}) => {
  const [categoryOptions, setCategoryOptions] = useState<any[]>([]);
  const [subcatOptions, setSubcatOptions] = useState<any[]>([]);
  const [sourceOptions, setSourceOptions] = useState<any[]>([]);

  const [cat, setCat] = useState("");
  const [subCat, setSubCat] = useState("");
  const [source, setSource] = useState("");

  const [loadingCats, setLoadingCats] = useState(false);
  const [loadingSubcats, setLoadingSubcats] = useState(false);
  const [loadingSources, setLoadingSources] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [uploadOpen, setUploadOpen] = useState(false);

  /** Load categories on mount (first expand) */

  useEffect(() => {
    if (categoryOptions.length > 0) return; // Already loaded → do nothing

    let cancelled = false;

    (async () => {
      try {
        setLoadingCats(true);
        const cats = await LookupsService.fetchBgmCategories([2], undefined, true);
        if (!cancelled) {
          setCategoryOptions(
            (cats ?? []).map((c: any) => ({
              label: c.name ?? "Unnamed category",
              value: c.id ?? "",
            })),
          );
        }
      } catch (e) {
        if (!cancelled) {
          console.error(e);
          setErrorMessage(
            "Failed to load Emissions categories. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setLoadingCats(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

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
      const subs = await LookupsService.fetchBgmSubcategories([2], categoryId, undefined, true);
      setSubcatOptions(
        (subs ?? []).map((s: any) => ({
          label: s.name ?? "",
          value: s.id ?? "",
        })),
      );
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
      const sources = await LookupsService.fetchBgmSources([2], subcatId, undefined, true);
      setSourceOptions(
        (sources ?? []).map((sr: any) => ({
          label: sr.name ?? "",
          value: sr.id ?? "",
        })),
      );
    } catch (e) {
      console.error(e);
      setSourceOptions([]);
      setErrorMessage("Failed to load Emissions sources.");
    } finally {
      setLoadingSources(false);
    }
  };

  const canAdd = Boolean(activeStage && cat && subCat && source);

  const findLabel = (value: string, options: any[]) =>
    options.find((o) => o.value === value)?.label ?? value;

  const handleAdd = () => {
    if (!canAdd) return;

    // Resolve labels from the loaded options
    const categoryLabel = findLabel(cat, categoryOptions);
    const subcatLabel = findLabel(subCat, subcatOptions);
    const sourceLabel = findLabel(source, sourceOptions);

    onAddManual({
      stageOrActivity: activeStage,
      category: categoryLabel,
      subCategory: subcatLabel,
      source: sourceLabel,
    });

    // Reset all dropdown selections and dependent options
    setCat("");
    setSubCat("");
    setSource("");
    setSubcatOptions([]);
    setSourceOptions([]);

    // Optional: clear any previous error
    setErrorMessage(null);
  };

  /** Template download: headers only (exact spec) */
  const downloadTemplate = () => {
    downloadCsv(
      RB_COLUMNS,
      [], // no rows → header-only template
      "emissions_sources_template.csv",
      true,
      true,
    );
  };

  return (
    <div className="relative rounded-[var(--radius-3)] border border-neutral-90/10 bg-white p-4">
      <div className="mb-2 text-base text-text-dark">{activeStage}</div>
      <div className="mb-6.25 text-xs text-text-faint">
        Select all emissions sources required to be reported under{" "}
        {activeStage.toLowerCase()}.
      </div>

      {/* Actions: Upload / Download template */}
      <div className="mb-10 grid grid-cols-1 gap-2 md:grid-cols-2">
        <button
          type="button"
          onClick={() => setUploadOpen(true)}
          className="flex w-full items-center justify-center gap-2 border border-border-input bg-white px-3 py-2 text-sm hover:bg-neutral-90 cursor-pointer"
        >
          <span className="material-symbols-rounded text-sm">upload_file</span>
          <span className="text-sm font-medium">Upload file</span>
        </button>

        <button
          type="button"
          className="flex w-full items-center justify-center gap-2 border border-border-input bg-white px-3 py-2 text-sm hover:bg-neutral-90 cursor-pointer"
          onClick={downloadTemplate}
        >
          <span className="material-symbols-rounded text-sm">download</span>
          <span className="text-sm font-medium">Download template</span>
        </button>
      </div>

      {/* Error message */}
      {errorMessage && (
        <div className="text-sm text-primary mb-4" role="alert">
          {errorMessage}
        </div>
      )}

      {/* Divider "or add manually" */}
      <div className="my-3 mb-8 flex items-center gap-4">
        <div className="h-px grow bg-neutral-200" />
        <div className="text-xs text-text-faint">or add manually</div>
        <div className="h-px grow bg-neutral-200" />
      </div>

      {/* Manual add inputs (Category - Sub-category - Source) */}
      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        {/* Category */}
        <div className="flex flex-col">
          <SelectListbox
            value={cat}
            onChange={(v: string) => handleChangeCat(v)}
            options={categoryOptions}
            label="Emissions category"
            aria-label="Emissions category"
            placeholder=""
            disabled={loadingCats}
          />
        </div>

        {/* Sub-category */}
        <div className="flex flex-col">
          <SelectListbox
            value={subCat}
            onChange={(v: string) => handleChangeSubcat(v)}
            options={subcatOptions}
            label="Emissions sub-category"
            aria-label="Emissions sub-category"
            placeholder=""
            disabled={!cat && loadingSubcats}
          />
        </div>

        {/* Source */}
        <div className="flex flex-col">
          <SelectListbox
            value={source}
            onChange={(v: string) => setSource(v)}
            options={sourceOptions}
            label="Emissions source"
            aria-label="Emissions source"
            placeholder=""
            disabled={!subCat && loadingSources}
          />
        </div>
      </div>

      {/* Add action */}
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          className="rounded bg-white px-6 py-2 text-sm font-semibold text-primary disabled:cursor-not-allowed disabled:opacity-50"
          onClick={handleAdd}
          disabled={!canAdd}
        >
          Add
        </button>
      </div>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        maxSizeMB={50}
        accept=".csv,.xlsx"
        parseFile={(file) =>
          parseFileToRows(file, rbConstructionUploadConfig.fileHeaders)
        }
        validateRows={(rows) =>
          validateRows(rows, rbConstructionUploadConfig.rules)
        }
        onSuccess={async (validRows) => {
          try {
            if (!categoryOptions.length) {
              const cats = await LookupsService.fetchBgmCategories([2],undefined,true);
              setCategoryOptions(
                (cats ?? []).map((c: any) => ({
                  label: c.name ?? "",
                  value: c.id ?? "",
                })),
              );
            }

            const normalize = (s: string) => s.trim().toLowerCase();
            const matchOption = (raw: string, options: any[]): string => {
              if (!raw) return "";
              const exact = options.find((o) => o.value === raw)?.value;
              if (exact) return exact;
              const lower = normalize(raw);
              return (
                options.find((o) => normalize(o.label) === lower)?.value || ""
              );
            };

            const resolveLabel = (value: string, options: any[]): string =>
              options.find((o) => o.value === value)?.label ??
              options.find((o) => o.label === value)?.label ??
              value;

            const imported: EmissionRow[] = [];

            for (const r of validRows) {
              const catRaw = String(r.category ?? "");
              const subRaw = String(r.subCategory ?? "");
              const srcRaw = String(r.source ?? "");

              // const catId = matchOption(catRaw, categoryOptions);

              const catValue = matchOption(catRaw, categoryOptions);
              const catLabel = resolveLabel(catValue, categoryOptions);

              let subcats: any[] = [];
              if (catValue) {
                const subs = await LookupsService.fetchBgmSubcategories(
                  [2],
                  catValue,
                );
                subcats = (subs ?? []).map((s) => ({
                  label: s.name,
                  value: s.id,
                }));
              }
              // const subId = matchOption(subRaw, subcats);

              const subValue = matchOption(
                String(r.subCategory ?? ""),
                subcats,
              );
              const subLabel = resolveLabel(subValue, subcats);

              let sources: any[] = [];
              if (subValue) {
                const srcs = await LookupsService.fetchBgmSources(
                  [2],
                  subValue,
                );
                sources = (srcs ?? []).map((s) => ({
                  label: s.name,
                  value: s.id,
                }));
              }
              // const srcId = matchOption(srcRaw, sources);

              const srcValue = matchOption(String(r.source ?? ""), sources);
              const srcLabel = resolveLabel(srcValue, sources);

              imported.push({
                id: crypto.randomUUID(),
                origin: "uploaded",
                stageOrActivity: activeStage,
                category: catLabel || catRaw,
                subCategory: subLabel || subRaw,
                source: srcLabel || srcRaw,
              });
            }

            onUploadParsed?.(imported);
            setErrorMessage(null);
            setUploadOpen(false);
          } catch (err: any) {
            console.error(err);
            setErrorMessage(err?.message || "Failed to import uploaded file.");
            throw err; // ensures UploadModal shows error state
          }
        }}
      />
    </div>
  );
};

type RBOperationsPanelProps = {
  onAddManual: (row: Omit<EmissionRow, "id" | "origin">) => void;
  onUploadParsed?: (rows: EmissionRow[]) => void;
};

const RBOperationsPanel: React.FC<RBOperationsPanelProps> = ({
  onAddManual,
  onUploadParsed,
}) => {
  const [allEquipment, setAllEquipment] = useState<
    { group_name: string; item: string }[]
  >([]);
  const [groupOptions, setGroupOptions] = useState<any[]>([]);
  const [itemOptions, setItemOptions] = useState<any[]>([]);
  const [group, setGroup] = useState("");
  const [item, setItem] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  useEffect(() => {
    if (allEquipment.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const res = await http.get<{ group_name: string; item: string }[]>(
          "/api/operational-equipment",
          { params: { limit: 500 } },
        );
        if (cancelled) return;
        const data = res.data ?? [];
        setAllEquipment(data);
        const uniqueGroups = Array.from(new Set(data.map((e) => e.group_name)))
          .sort()
          .map((g) => ({ label: g, value: g }));
        setGroupOptions(uniqueGroups);
      } catch (e) {
        if (!cancelled)
          setErrorMessage("Failed to load operational equipment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleGroupChange = (g: string) => {
    setGroup(g);
    setItem("");
    const items = allEquipment
      .filter((e) => e.group_name === g)
      .map((e) => ({ label: e.item, value: e.item }));
    setItemOptions(items);
  };

  const canAdd = Boolean(group && item);

  const handleAdd = () => {
    if (!canAdd) return;
    onAddManual({
      stageOrActivity: "Operations",
      category: group,
      subCategory: item,
      source: "",
    });
    setGroup("");
    setItem("");
    setItemOptions([]);
    setErrorMessage(null);
  };

  const downloadTemplate = () => {
    downloadCsv(
      RB_OPERATIONS_COLUMNS,
      [],
      "operations_sources_template.csv",
      true,
      true,
    );
  };


  return (
    <div className="relative rounded-[var(--radius-3)] border border-neutral-90/10 bg-white p-4">
      <div className="mb-2 text-base text-text-dark">Operations</div>
      <div className="mb-6.25 text-xs text-text-faint">
        Select all emissions sources required to be reported under operations.
      </div>

      <div className="mb-10 grid grid-cols-1 gap-2 md:grid-cols-2">
        <button
          type="button"
          onClick={() => setUploadOpen(true)}
        >
          Upload file
        </button>
        <button
          type="button"
          className="flex w-full items-center justify-center gap-2 border border-border-input bg-white px-3 py-2 text-sm hover:bg-neutral-90 cursor-pointer"
          onClick={downloadTemplate}
        >
          <span className="material-symbols-rounded text-sm">download</span>
          <span className="text-sm font-medium">Download template</span>
        </button>
      </div>

      {errorMessage && (
        <div className="text-sm text-primary mb-4" role="alert">
          {errorMessage}
        </div>
      )}

      <div className="my-3 mb-8 flex items-center gap-4">
        <div className="h-px grow bg-neutral-200" />
        <div className="text-xs text-text-faint">or add manually</div>
        <div className="h-px grow bg-neutral-200" />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <SelectListbox
          value={group}
          onChange={handleGroupChange}
          options={groupOptions}
          label="Group"
          placeholder=""
          disabled={loading}
        />
        <SelectListbox
          value={item}
          onChange={setItem}
          options={itemOptions}
          label="Item"
          placeholder=""
          disabled={!group}
        />
      </div>
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          className="rounded bg-white px-6 py-2 text-sm font-semibold text-primary disabled:cursor-not-allowed disabled:opacity-50"
          onClick={handleAdd}
          disabled={!canAdd}
        >
          Add
        </button>
      </div>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        maxSizeMB={50}
        accept=".csv,.xlsx"
        parseFile={(file) =>
          parseFileToRows(file, rbOperationsUploadConfig.fileHeaders)
        }
        validateRows={(rows) =>
          validateRows(rows, rbOperationsUploadConfig.rules)
        }
        onSuccess={(validRows) => {
          const imported: EmissionRow[] = validRows.map((r) => ({
            id: crypto.randomUUID(),
            origin: "uploaded",
            stageOrActivity: "Operations",
            category: r.group,          // Group → category
            subCategory: r.item,        // Item → subCategory
            source: "",
          }));

          onUploadParsed?.(imported);
          setUploadOpen(false);
          setErrorMessage(null);
        }}
      />

    </div>
  );
};

type RBMaintenancePanelProps = {
  onAddManual: (row: Omit<EmissionRow, "id" | "origin">) => void;
  onUploadParsed?: (rows: EmissionRow[]) => void;
};

const RBMaintenancePanel: React.FC<RBMaintenancePanelProps> = ({
  onAddManual,
  onUploadParsed,
}) => {
  const [allFactors, setAllFactors] = useState<
    { activity_type: string; item: string }[]
  >([]);
  const [activityOptions, setActivityOptions] = useState<any[]>([]);
  const [itemOptions, setItemOptions] = useState<any[]>([]);
  const [activityType, setActivityType] = useState("");
  const [item, setItem] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [uploadOpen, setUploadOpen] = useState(false);

  useEffect(() => {
    if (allFactors.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const res = await http.get<{ activity_type: string; item: string }[]>(
          "/api/maintenance-replacement-factors/active",
          {
            params: {
              use_org_jurisdiction: true,
            },
          }
        );
        if (cancelled) return;
        const data = res.data ?? [];
        setAllFactors(data);
        const uniqueTypes = Array.from(
          new Set(data.map((f) => f.activity_type)),
        )
          .sort()
          .map((t) => ({ label: t, value: t }));
        setActivityOptions(uniqueTypes);
      } catch (e) {
        if (!cancelled)
          setErrorMessage("Failed to load maintenance activities.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleActivityChange = (t: string) => {
    setActivityType(t);
    setItem("");
    const items = allFactors
      .filter((f) => f.activity_type === t)
      .map((f) => ({ label: f.item, value: f.item }));
    setItemOptions(items);
  };

  const canAdd = Boolean(activityType && item);

  const handleAdd = () => {
    if (!canAdd) return;
    onAddManual({
      stageOrActivity: "Maintenance",
      category: activityType,
      subCategory: item,
      source: "",
    });
    setActivityType("");
    setItem("");
    setItemOptions([]);
    setErrorMessage(null);
  };

  const downloadTemplate = () => {
    downloadCsv(
      RB_MAINTENANCE_COLUMNS,
      [],
      "maintenance_sources_template.csv",
      true,
      true,
    );
  };

  return (
    <div className="relative rounded-[var(--radius-3)] border border-neutral-90/10 bg-white p-4">
      <div className="mb-2 text-base text-text-dark">Maintenance</div>
      <div className="mb-6.25 text-xs text-text-faint">
        Select all emissions sources required to be reported under maintenance.
      </div>

      <div className="mb-10 grid grid-cols-1 gap-2 md:grid-cols-2">
        <button
          type="button"
          onClick={() => setUploadOpen(true)}
          className = "cursor-pointer"
        >
          Upload file
        </button>
        <button
          type="button"
          className="flex w-full items-center justify-center gap-2 border border-border-input bg-white px-3 py-2 text-sm hover:bg-neutral-90 cursor-pointer"
          onClick={downloadTemplate}
        >
          <span className="material-symbols-rounded text-sm">download</span>
          <span className="text-sm font-medium">Download template</span>
        </button>
      </div>

      {errorMessage && (
        <div className="text-sm text-primary mb-4" role="alert">
          {errorMessage}
        </div>
      )}

      <div className="my-3 mb-8 flex items-center gap-4">
        <div className="h-px grow bg-neutral-200" />
        <div className="text-xs text-text-faint">or add manually</div>
        <div className="h-px grow bg-neutral-200" />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <SelectListbox
          value={activityType}
          onChange={handleActivityChange}
          options={activityOptions}
          label="Activity type"
          placeholder=""
          disabled={loading}
        />
        <SelectListbox
          value={item}
          onChange={setItem}
          options={itemOptions}
          label="Item"
          placeholder=""
          disabled={!activityType}
        />
      </div>
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          className="rounded bg-white px-6 py-2 text-sm font-semibold text-primary disabled:cursor-not-allowed disabled:opacity-50"
          onClick={handleAdd}
          disabled={!canAdd}
        >
          Add
        </button>
      </div>
      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        maxSizeMB={50}
        accept=".csv,.xlsx"
        parseFile={(file) =>
          parseFileToRows(file, rbMaintenanceUploadConfig.fileHeaders)
        }
        validateRows={(rows) =>
          validateRows(rows, rbMaintenanceUploadConfig.rules)
        }
        onSuccess={(validRows) => {
          const imported: EmissionRow[] = validRows.map((r) => ({
            id: crypto.randomUUID(),
            origin: "uploaded",
            stageOrActivity: "Maintenance",
            category: r.activityType,   // Activity type → category
            subCategory: r.item,        // Item → subCategory
            source: "",
          }));

          onUploadParsed?.(imported);
          setUploadOpen(false);
          setErrorMessage(null);
        }}
      />
    </div>
  );
};

/** ---- ReportingBoundarySmall ---- */
export type ReportingBoundarySmallProps = {
  value: EmissionRow[];
  onChange: (rows: EmissionRow[]) => void;
  initialStages?: string[];
  defaultExpanded?: boolean;
};

const ReportingBoundarySmall: React.FC<ReportingBoundarySmallProps> = ({
  value,
  onChange,
  initialStages = [],
  defaultExpanded = false,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [selectedStages, setSelectedStages] = useState<string[]>(initialStages);
  const [activeStage, setActiveStage] = useState<string | null>(null);

  /** Only show check when at least one emission added */
  const isComplete = value.length > 0;

  const stageChips: ChipItem[] = useMemo(
    () => selectedStages.map((s) => ({ id: s, label: s })),
    [selectedStages],
  );

  const handleStagesChange = (next: string[]) => {
    setSelectedStages(next);
    if (activeStage && !next.includes(activeStage)) setActiveStage(null);
  };

  const addManualRow = (row: Omit<EmissionRow, "id" | "origin">) => {
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    onChange([...value, { ...row, id, origin: "manual" }]);
  };

  const addUploadedRows = (rows: EmissionRow[]) => {
    onChange([...value, ...rows]);
  };

  // 3‑state icon logic
  const getStatusIcon = () => {
    if (isComplete) return "check_circle";
    if (expanded) return "radio_button_partial";
    return "radio_button_unchecked";
  };

  return (
    <div className="p-4 border-t border-neutral-200">
      {/* Header */}
      <button
  type="button"
  onClick={() => setExpanded((v) => !v)}
  className="mb-8 w-full flex items-center justify-between gap-2 text-left cursor-pointer"
  aria-expanded={expanded}
  aria-controls="reporting-boundary-small-panel"
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
      Reporting boundary (optional)
    </span>
  </div>

  <span className="material-symbols-rounded shrink-0">
    {expanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
  </span>
</button>


      {expanded && (
        <div
          id="reporting-boundary-small-panel"
          className="space-y-4 mb-7 rounded-md bg-bg-content"
        >
          {/* Dropdown (no ticks; chips inside the field) */}
          <MultiSelectDropdown
            label="Project lifecycle stage"
            options={LIFECYCLE_OPTIONS}
            selected={selectedStages}
            onChange={handleStagesChange}
            placeholder="Select all that apply"
            withSearch={false}
            closeOnSelect={false}
            className="mb-10"
          />

          {/* Chips list + helper text */}
          {selectedStages.length > 0 && (
            <div>
              <div className="mb-2 mt-1 text-text-base text-text-dark">
                <div>Selected project lifecycle stages</div>
                <div className="text-sm mt-1 text-text-faint">
                  Choose a project lifecycle stage to start adding emissions
                  sources
                </div>
              </div>
              <ChipsRow
                items={stageChips}
                activeId={activeStage}
                onActivate={(id) =>
                  setActiveStage((prev) => (prev === id ? null : id))
                }
                onRemove={(id) =>
                  handleStagesChange(selectedStages.filter((x) => x !== id))
                }
                wrap={false}
                align="left"
                size="md"
                className="mt-4"
              />
            </div>
          )}

          {/* Stage-specific entry panel (on chip click) */}
          {activeStage &&
            selectedStages.includes(activeStage) &&
            (activeStage === "Construction" ? (
              <RBOperationPanel
                activeStage={activeStage}
                onAddManual={addManualRow}
                onUploadParsed={addUploadedRows}
                onClose={() => setActiveStage(null)}
              />
            ) : activeStage === "Operations" ? (
              <RBOperationsPanel
                onAddManual={addManualRow}
                onUploadParsed={addUploadedRows}
              />
            ) : (
              <RBMaintenancePanel
                onAddManual={addManualRow}
                onUploadParsed={addUploadedRows}
              />
            ))}

          {value.some((r) => r.stageOrActivity === "Construction") && (
            <div className="mt-8">
              <div className="mb-2 text-base text-text-dark">
                Construction — Emissions sources
              </div>
              <EmissionTable
                rows={value.filter((r) => r.stageOrActivity === "Construction")}
                // leadingHeader="Project lifecycle stage"
                col2Header="Emissions category"
                col3Header="Emissions sub-category"
                showSource={true}
                showOrigin={false}
                showQuantity={false}
              />
            </div>
          )}
          {value.some((r) => r.stageOrActivity === "Operations") && (
            <div className="mt-8">
              <div className="mb-2 text-base text-text-dark">
                Operations — Emissions sources
              </div>
              <EmissionTable
                rows={value.filter((r) => r.stageOrActivity === "Operations")}
                // leadingHeader="Project lifecycle stage"
                col2Header="Group"
                col3Header="Item"
                showSource={false}
                showOrigin={false}
                showQuantity={false}
              />
            </div>
          )}
          {value.some((r) => r.stageOrActivity === "Maintenance") && (
            <div className="mt-8">
              <div className="mb-2 text-base text-text-dark">
                Maintenance — Emissions sources
              </div>
              <EmissionTable
                rows={value.filter((r) => r.stageOrActivity === "Maintenance")}
                // leadingHeader="Project lifecycle stage"
                col2Header="Activity type"
                col3Header="Item"
                showSource={false}
                showOrigin={false}
                showQuantity={false}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ReportingBoundarySmall;
