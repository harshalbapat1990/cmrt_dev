import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import LookupsService from "../services/Lookups.service";
import ActivityDataService from "../services/ActivityData.service";
import ReportDataService from "../services/ReportData.service";
import { ProjReportSubmissionsService } from "../services/ProjectReportSubmissions.service";

const submissionsService = new ProjReportSubmissionsService();
import { SelectListbox } from "../components/common/Select";
import { NumericInput } from "./common/NumericInput";
import Help from "../assets/icons/help.svg";
import ArrowUp from "../assets/icons/arrow-up.svg";
import Download from "../assets/icons/download.svg";
import UploadFile from "../assets/icons/upload_file.svg";
import Add from "../assets/icons/add.svg";
import Lock from "../assets/icons/lock.svg";
import type { Row, ReportDataProps } from "../types/reports";
import { monthLabelToKey, toNumberSafe } from "../utils/utils";

import { downloadCsv, type CsvColumn } from "../utils/downloadCsv";
import { uploadCsv, type ParsedRow } from "../utils/uploadCsv";


type EditingCellMap = Record<string, Partial<Record<keyof Row, boolean>>>;

const prevKey = (key: string): string => {
  const [yStr, mStr] = key.split("-");
  let y = Number(yStr);
  let m = Number(mStr);
  if (!y || !m) return "";
  m -= 1;
  if (m === 0) {
    m = 12;
    y -= 1;
  }
  return `${y}-${String(m).padStart(2, "0")}`;
};

const formatNumber = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 2 });

const addInput =
  "w-full h-10 px-3 border border-border-input rounded-[var(--radius-3)] text-sm text-text-dark bg-white focus:outline-none focus:ring-1 focus:ring-text-dark focus:border-transparent";
const readOnlyText = "min-h-10 h-10 flex items-center text-sm text-text-dark cursor-not-allowed";
const borderlessText = "min-h-10 h-10 flex items-center text-sm text-text-dark bg-white cursor-pointer";

const dataQualityOptionsFormatted: any = [
  { value: "estimated", label: "Estimated" },
  { value: "monitored", label: "Monitored" },
];

// Columns for Materials data (IDs strongly recommended for robust imports)
const MATERIAL_COLUMNS: CsvColumn[] = [
  { key: "subCategory", label: "Emissions sub-category" },
  { key: "source", label: "Emissions source" },
  { key: "unit", label: "Unit" },
  { key: "dataQuality", label: "Data quality" },
  { key: "quantity", label: "Quantity (unit)" },
  { key: "emissions", label: "Emissions (tCO₂e)" },
  { key: "notes", label: "Notes / Comments (optional)" },
];

const TABLE_KEY = "recurring_materials";

const ReportData: React.FC<ReportDataProps> = ({
  reportId,
  currentReport,
  reportStatus,
  projectId,
  stageInstanceId,
  submissionPeriodId,
  onSubmit,
  onApprove,
  canEditStage,
  canAdminStage,
}) => {

  const [expanded, setExpanded] = useState(true);
  const [rows, setRows] = useState<Row[]>([]);
  const [editingCell, setEditingCell] = useState<EditingCellMap>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [execSummary, setExecSummary] = useState<string>("");
  const charLimit = 1000;
  const charCount = execSummary.length;

  const [subCategoryOptions, setSubCategoryOptions] = useState<any[]>([]);
  const [sourceOptionsByRow, setSourceOptionsByRow] = useState<Record<string, any[] | null>>({});
  const [unitOptionsByRow, setUnitOptionsByRow] = useState<Record<string, any[]>>({});
  const [loadingSubcats, setLoadingSubcats] = useState(false);
  const [loadingRows, setLoadingRows] = useState<Record<string, { sources?: boolean; units?: boolean }>>({});
  const [emissionsLoadingByRow, setEmissionsLoadingByRow] = useState<Record<string, boolean>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // All activity rows across periods — used for monthly totals
  const [allEntries, setAllEntries] = useState<any[]>([]);
  const [periodLabelMap, setPeriodLabelMap] = useState<Record<string, string>>({});
  const [summaryLoading, setSummaryLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!projectId) return;
    submissionsService.fetchStages(projectId)
      .then((stages) => {
        const map: Record<string, string> = {};
        for (const s of stages) {
          if (s.id && s.period_label) map[s.id] = s.period_label;
        }
        setPeriodLabelMap(map);
      })
      .catch(() => {});
  }, [projectId]);

  const emissionReqSeqRef = useRef<Record<string, number>>({});
  const rowsRef = useRef<Row[]>(rows);
  useEffect(() => {
    rowsRef.current = rows;
  }, [rows]);

  const canEdit =
    canEditStage &&
    (reportStatus === "Not Started" || reportStatus === "In Progress");
  const canApprove = canAdminStage && reportStatus === "Awaiting approval";

  const subcatLabelById = useMemo(
    () => Object.fromEntries(subCategoryOptions.map((o) => [o.value, o.label])),
    [subCategoryOptions]
  );

  const sourceLabelMap = useMemo(() => {
    const map: Record<string, string> = {};
    Object.values(sourceOptionsByRow).forEach((arr) => {
      (arr || []).forEach((o) => {
        map[o.value] = o.label;
      });
    });
    return map;
  }, [sourceOptionsByRow]);

  const unitLabelMap = useMemo(() => {
    const map: Record<string, string> = {};
    Object.values(unitOptionsByRow).forEach((arr) => {
      (arr || []).forEach((o) => {
        map[o.value] = o.label;
      });
    });
    return map;
  }, [unitOptionsByRow]);

  const labelForSource = (rowId: string, _subCategoryId?: string, sourceId?: string) => {
    if (!sourceId) return "—";
    const rowOpts = sourceOptionsByRow[rowId] || [];
    const found = rowOpts.find((o) => o.value === sourceId);
    return found?.label ?? sourceLabelMap[sourceId] ?? sourceId;
  };
  const labelForUnit = (rowId: string, _sourceId?: string, unitId?: string) => {
    if (!unitId) return "—";
    const rowOpts = unitOptionsByRow[rowId] || [];
    const found = rowOpts.find((o) => o.value === unitId);
    return found?.label ?? unitLabelMap[unitId] ?? unitId;
  };

  const ensureSubcategoriesLoaded = useCallback(async () => {
    if (subCategoryOptions.length || loadingSubcats) return;
    try {
      setLoadingSubcats(true);
      const opts = await LookupsService.fetchSubCategories();
      // setSubCategoryOptions(opts);
       setSubCategoryOptions(
        (opts ?? []).map((s: any) => ({
          label: s.name ?? s.sub_category_name ?? "",
          value: s.id ?? s.sub_category_id ?? "",
        }))
      );
    } catch (e) {
      console.error(e);
      setErrorMessage("Failed to load sub-categories. Please try again.");
    } finally {
      setLoadingSubcats(false);
    }
  }, [subCategoryOptions.length, loadingSubcats]);

  useEffect(() => {
    if (expanded) void ensureSubcategoriesLoaded();
  }, [expanded, ensureSubcategoriesLoaded]);

  const mapEntryToRow = (e: any): Row => ({
    id: e.id || crypto.randomUUID(),
    apiId: e.id || undefined,
    isNew: false,
    isFromUpload: false,
    subCategory: e.extra_fields?.emissions_sub_category_id ?? "",
    source: e.extra_fields?.emission_source_id ?? "",
    unit: e.unit_id ?? "",
    dataQuality: e.extra_fields?.data_quality ?? "",
    quantity: toNumberSafe(e.quantity),
    emissions: e.extra_fields?.emissions_tco2e != null
      ? toNumberSafe(e.extra_fields.emissions_tco2e).toFixed(2)
      : "",
    notes: e.extra_fields?.notes ?? "",
  });

  // Load rows for the current submission period
  useEffect(() => {
    if (!stageInstanceId || !submissionPeriodId) return;
    let cancelled = false;
    setSummaryLoading(true);

    (async () => {
      try {
        await ensureSubcategoriesLoaded();

        const apiRows = await ActivityDataService.fetchRows(
          stageInstanceId,
          TABLE_KEY,
          null,
          submissionPeriodId,
        );
        if (cancelled) return;

        const tableRows = apiRows.map(mapEntryToRow);
        setRows(tableRows);

        // Prime sources & units in parallel and batch-set once
        const sourceEntries = await Promise.all(
          tableRows.map(async (r) => {
            if (!r.subCategory) return [r.id, []] as [string, any[]];
            try {
              const sources = await LookupsService.fetchSources(r.subCategory);
              return [r.id, sources] as [string, any[]];
            } catch {
              return [r.id, []] as [string, any[]];
            }
          })
        );

        const unitEntries = await Promise.all(
          tableRows.map(async (r) => {
            if (!r.source) return [r.id, []] as [string, any[]];
            try {
              const units = await LookupsService.fetchUnits();
              return [r.id, units] as [string, any[]];
            } catch {
              return [r.id, []] as [string, any[]];
            }
          })
        );
        setSourceOptionsByRow(Object.fromEntries(sourceEntries));
        setUnitOptionsByRow(Object.fromEntries(unitEntries));
      } catch (err) {
        console.error("Failed to fetch activity data:", err);
        if (!cancelled) {
          setRows([]);
          setSourceOptionsByRow({});
          setUnitOptionsByRow({});
        }
      } finally {
        if (!cancelled) setSummaryLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [stageInstanceId, submissionPeriodId, ensureSubcategoriesLoaded]);

  // Load all entries (all periods) for the monthly totals summary cards
  useEffect(() => {
    if (!stageInstanceId) return;
    let cancelled = false;
    (async () => {
      try {
        const all = await ActivityDataService.fetchRows(stageInstanceId, TABLE_KEY);
        if (!cancelled) setAllEntries(all);
      } catch {
        if (!cancelled) setAllEntries([]);
      }
    })();
    return () => { cancelled = true; };
  }, [stageInstanceId]);

  const currentRowsTotal = useMemo(() => {
    return rows.reduce((sum, r) => sum + toNumberSafe(r.emissions), 0);
  }, [rows]);

  const monthlyTotals = useMemo(() => {
    // Group all entries by their submission_period_id, then map to period label
    const byPeriod: Record<string, number> = {};
    for (const r of allEntries) {
      const pid = r.submission_period_id;
      if (!pid) continue;
      const e = toNumberSafe(r.extra_fields?.emissions_tco2e);
      byPeriod[pid] = Math.round(((byPeriod[pid] ?? 0) + e + Number.EPSILON) * 100) / 100;
    }
    // Re-key by period_label (month string) using periodLabelMap
    const totals: Record<string, number> = {};
    for (const [pid, total] of Object.entries(byPeriod)) {
      const label = periodLabelMap[pid];
      if (label) {
        const k = monthLabelToKey(label);
        if (k) totals[k] = (totals[k] ?? 0) + total;
      }
    }
    return totals;
  }, [allEntries, periodLabelMap]);

  const ymKey = useMemo(() => monthLabelToKey(currentReport), [currentReport]);
  const prevYmKey = useMemo(() => (ymKey ? prevKey(ymKey) : ""), [ymKey]);

  const thisPeriod = currentRowsTotal;
  const lastPeriod = prevYmKey ? monthlyTotals[prevYmKey] ?? 0 : 0;
  const totalReported = useMemo(() => {
    const baseTotal = Object.values(monthlyTotals).reduce((acc, v) => acc + (v ?? 0), 0);
    const priorCurrent = ymKey ? monthlyTotals[ymKey] ?? 0 : 0;
    return Math.round(((baseTotal - priorCurrent + currentRowsTotal) + Number.EPSILON) * 100) / 100;
  }, [monthlyTotals, currentRowsTotal, ymKey]);

  const handleAddRow = async () => {
    await ensureSubcategoriesLoaded();
    const newRow: Row = {
      id: crypto.randomUUID(),
      isNew: true,
      isFromUpload: false,
      subCategory: "",
      source: "",
      unit: "",
      dataQuality: "",
      quantity: null,
      emissions: "",
      notes: "",
    };

    setRows((prev) => [...prev, newRow]);
    setSourceOptionsByRow((prev) => ({ ...prev, [newRow.id]: [] }));
    setUnitOptionsByRow((prev) => ({ ...prev, [newRow.id]: [] }));
  };

  const startEdit = (rowId: string, field: keyof Row) => {
    if (!canEdit) return;
    setEditingCell((prev) => ({
      ...prev,
      [rowId]: { ...(prev[rowId] || {}), [field]: true },
    }));
  };

  const stopEdit = (rowId: string, field: keyof Row) => {
    setEditingCell((prev) => ({
      ...prev,
      [rowId]: { ...(prev[rowId] || {}), [field]: false },
    }));
  };

  const parseQuantity = (v: any): number | null => {
    if (v === "" || v === null || v === undefined) return null;
    const num = Number(v);
    return Number.isFinite(num) ? num : null;
  };

  const recomputeEmissions = async (rowId: string, overrides?: Partial<Row>) => {
    const current = rowsRef.current.find((r) => r.id === rowId);
    if (!current) return;

    const nextRow: Row = { ...current, ...(overrides || {}) };
    const { subCategory, source, unit, quantity } = nextRow;

    if (!subCategory || !source || !unit || quantity == null || !Number.isFinite(quantity)) {
      setRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, emissions: "" } : r)));
      return;
    }

    const seq = (emissionReqSeqRef.current[rowId] || 0) + 1;
    emissionReqSeqRef.current[rowId] = seq;
    setEmissionsLoadingByRow((prev) => ({ ...prev, [rowId]: true }));

    try {
      const totalEF = await ReportDataService.fetchEmissionValues(subCategory, source, unit);
      const emissionsVal = (quantity ?? 0) * (totalEF ?? 0);
      const emissionsStr = (Number.isFinite(emissionsVal) ? emissionsVal : 0).toFixed(2);

      if (emissionReqSeqRef.current[rowId] === seq) {
        setRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, emissions: emissionsStr } : r)));
      }
    } catch (err) {
      console.error("Failed to compute emissions:", err);
      if (emissionReqSeqRef.current[rowId] === seq) {
        setRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, emissions: "" } : r)));
      }
    } finally {
      if (emissionReqSeqRef.current[rowId] === seq) {
        setEmissionsLoadingByRow((prev) => ({ ...prev, [rowId]: false }));
      }
    }
  };

  const handleChange =
    (rowId: string, field: keyof Row) =>
      async (e: { target: { value: any } } | any) => {
        const value = e?.target?.value ?? e;
        const coerced = field === "quantity" ? parseQuantity(value) : value;

        setRows((prev) => prev.map((r) => (r.id !== rowId ? r : ({ ...r, [field]: coerced } as Row))));

        if (field === "quantity" || field === "subCategory" || field === "source" || field === "unit") {
          void recomputeEmissions(rowId, { [field]: coerced } as Partial<Row>);
        }
      };

  const handleSubcategoryChange = async (rowId: string, subcategoryId: string) => {
    handleChange(rowId, "subCategory")({ target: { value: subcategoryId } });
    handleChange(rowId, "source")({ target: { value: "" } });
    handleChange(rowId, "unit")({ target: { value: "" } });

    setLoadingRows((prev) => ({ ...prev, [rowId]: { ...(prev[rowId] || {}), sources: true } }));
    try {
      const options = await LookupsService.fetchSources(subcategoryId);
      setSourceOptionsByRow((prev) => ({ ...prev, [rowId]: options }));
      setUnitOptionsByRow((prev) => ({ ...prev, [rowId]: [] }));
    } catch (e) {
      console.error(e);
      setSourceOptionsByRow((prev) => ({ ...prev, [rowId]: [] }));
      setErrorMessage("Failed to load sources for the selected sub-category.");
    } finally {
      setLoadingRows((prev) => ({ ...prev, [rowId]: { ...(prev[rowId] || {}), sources: false } }));
    }
  };

  const handleSourceChangeCascading = async (rowId: string, sourceId: string) => {
    handleChange(rowId, "source")({ target: { value: sourceId } });
    handleChange(rowId, "unit")({ target: { value: "" } });

    setLoadingRows((prev) => ({ ...prev, [rowId]: { ...(prev[rowId] || {}), units: true } }));
    try {
      const options = await LookupsService.fetchUnits();
      setUnitOptionsByRow((prev) => ({ ...prev, [rowId]: options }));
    } catch (e) {
      console.error(e);
      setUnitOptionsByRow((prev) => ({ ...prev, [rowId]: [] }));
      setErrorMessage("Failed to load units for the selected source.");
    } finally {
      setLoadingRows((prev) => ({ ...prev, [rowId]: { ...(prev[rowId] || {}), units: false } }));
    }
  };

  const handleUploadClick = () => {
    if (!canEdit) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      await ensureSubcategoriesLoaded();

      //Parse using shared util with a robust header normalizer for the labels you shared
      const parsed: ParsedRow[] = await uploadCsv(file, {
        columns: MATERIAL_COLUMNS,
        normalizeHeader: (label: string) => {
          const s = label.trim().toLowerCase();

          if (s === "emissions sub-category" || s === "emissions sub category") return "subCategory";
          if (s === "emissions source" || s === "source") return "source";
          if (s === "unit") return "unit";
          if (s === "data quality" || s === "dataquality") return "dataQuality";
          if (s === "quantity (unit)" || s.startsWith("quantity")) return "quantity";

          if (s.startsWith("emissions (tco2e)")) return "emissions";

          if (s === "notes / comments (optional)" || s.includes("notes") || s.includes("comments")) return "notes";

          // fallback to exact label match from MATERIAL_COLUMNS
          const found = MATERIAL_COLUMNS.find(c => c.label.trim().toLowerCase() === s);
          return found ? found.key : "";
        },
        numericKeys: ["quantity", "emissions"],
      });

      // Helper: label → id, for sub-category names
      const subcatLabelToId: Record<string, string> =
        subCategoryOptions.reduce((acc, o) => {
          acc[o.label.trim().toLowerCase()] = o.value;
          return acc;
        }, {} as Record<string, string>);

      const importedRows = parsed.map((obj) => {
        const subcatName = String(obj.subCategory ?? "").trim();
        const sourceName = String(obj.source ?? "").trim();
        const unitName = String(obj.unit ?? "").trim();

        const qRaw = obj.quantity as any;
        const qNum =
          qRaw == null || qRaw === ""
            ? null
            : typeof qRaw === "number"
              ? qRaw
              : (() => {
                const n = Number(String(qRaw).replace(/,/g, ""));
                return Number.isFinite(n) ? n : null;
              })();

        const r: Row = {
          id: crypto.randomUUID(),
          isNew: true,
          isFromUpload: true,
          subCategory: subcatName,
          source: sourceName,
          unit: unitName,
          dataQuality: String(obj.dataQuality ?? ""),
          quantity: qNum,
          emissions: "", // computed later
          notes: String(obj.notes ?? ""),
        };
        return r;
      });

      //  Resolve NAMES -> IDs, then compute EF and emissions per row.
      const rowUpdates = await Promise.all(
        importedRows.map(async (r) => {
          let subCategoryId = "";
          let sourceId = "";
          let unitId = "";

          if (r.subCategory) {
            const key = r.subCategory.trim().toLowerCase();
            subCategoryId = subcatLabelToId[key] || "";
          }

          let sources: any = [];
          if (subCategoryId) {
            try {
              sources = await LookupsService.fetchSources(subCategoryId);
            } catch {
              sources = [];
            }
          }
          const sourceLabelToId: Record<string, string> = sources.reduce((acc: any, o: any) => {
            acc[o.label.trim().toLowerCase()] = o.value;
            return acc;
          }, {} as Record<string, string>);

          if (r.source) {
            const key = r.source.trim().toLowerCase();
            sourceId = sourceLabelToId[key] || "";
          }

          let units: any[] = [];
          if (sourceId) {
            try {
              units = await LookupsService.fetchUnits();
            } catch {
              units = [];
            }
          }
          const unitLabelToId: Record<string, string> = units.reduce((acc, o) => {
            acc[o.label.trim().toLowerCase()] = o.value;
            return acc;
          }, {} as Record<string, string>);

          if (r.unit) {
            const key = r.unit.trim().toLowerCase();
            unitId = unitLabelToId[key] || "";
          }

          // Compute EF and emissions
          let emissionsStr = "";
          if (subCategoryId && sourceId && unitId && r.quantity != null) {
            try {
              const ef = await ReportDataService.fetchEmissionValues(subCategoryId, sourceId, unitId);
              const efNum =
                ef == null
                  ? 0
                  : typeof ef === "number"
                    ? ef
                    : Number(String(ef).replace(/,/g, "")) || 0;
              const qty = typeof r.quantity === "number" ? r.quantity : Number(r.quantity) || 0;
              const val = qty * efNum;
              emissionsStr = (Number.isFinite(val) ? val : 0).toFixed(2);
            } catch {
              emissionsStr = "";
            }
          }

          return {
            rowId: r.id,
            subCategoryId,
            sourceId,
            unitId,
            sources,
            units,
            emissionsStr,
          };
        })
      );

      // Apply all updates to state in a single batch
      const nextSourceOptions: Record<string, any[]> = {};
      const nextUnitOptions: Record<string, any[]> = {};
      const idUpdates: Record<string, { subCategory: string; source: string; unit: string; emissions: string }> = {};

      for (const u of rowUpdates) {
        nextSourceOptions[u.rowId] = u.sources;
        nextUnitOptions[u.rowId] = u.units;
        idUpdates[u.rowId] = {
          subCategory: u.subCategoryId || "",
          source: u.sourceId || "",
          unit: u.unitId || "",
          emissions: u.emissionsStr || "",
        };
      }

      setRows((prev) =>
        [
          ...prev,
          ...importedRows.map((r) => {
            const upd = idUpdates[r.id];
            return upd
              ? {
                ...r,
                subCategory: upd.subCategory,
                source: upd.source,
                unit: upd.unit,
                emissions: upd.emissions,
              }
              : r;
          }),
        ]
      );

      setSourceOptionsByRow((prev) => ({ ...prev, ...nextSourceOptions }));
      setUnitOptionsByRow((prev) => ({ ...prev, ...nextUnitOptions }));

      setErrorMessage(null);
    } catch (err) {
      console.error(err);
      setErrorMessage("Failed to parse or import the uploaded file.");
    } finally {
      e.target.value = "";
    }
  };

  const validateRows = (): string | null => {
    for (const r of rows) {
      if (!r.subCategory) return "Please select an Emissions sub-category.";
      if (!r.source) return "Please select an Emissions source.";
      if (!r.unit) return "Please select a Unit.";
      if (!r.dataQuality) return "Please select Data quality.";
      if (r.quantity === null || r.quantity === undefined) return "Please enter a Quantity.";
    }
    return null;
  };

  const canPostRow = (r: Row) =>
    Boolean(
      r.subCategory &&
      r.source &&
      r.unit &&
      r.dataQuality &&
      r.quantity !== null &&
      r.quantity !== undefined &&
      r.emissions !== ""
    );

  const handleLocalSubmit = async () => {
    if (!canEditStage) return;

    const err = validateRows();
    if (err) {
      setErrorMessage(err);
      return;
    }
    setErrorMessage(null);

    if (!stageInstanceId || !submissionPeriodId || !projectId) {
      setErrorMessage("Project context not loaded yet. Please wait and try again.");
      return;
    }

    const rowsToCreate = rows.filter((r) => !r.apiId && canPostRow(r));
    if (rowsToCreate.length === 0) {
      onSubmit();
      return;
    }

    try {
      const results = await Promise.allSettled(
        rowsToCreate.map((r) =>
          ActivityDataService.createRow({
            project_id: projectId,
            project_stage_instance_id: stageInstanceId,
            ui_table_key: TABLE_KEY,
            quantity: toNumberSafe(r.quantity),
            unit_id: r.unit || undefined,
            submission_period_id: submissionPeriodId,
            extra_fields: {
              emissions_sub_category_id: r.subCategory,
              emission_source_id: r.source,
              data_quality: r.dataQuality,
              notes: r.notes ?? "",
              emissions_tco2e: toNumberSafe(r.emissions),
            },
          })
        )
      );

      const idByTempId: Record<string, string> = {};
      results.forEach((res, idx) => {
        const tempRow = rowsToCreate[idx];
        if (res.status === "fulfilled") {
          const saved = res.value as { id?: string };
          if (saved?.id) idByTempId[tempRow.id] = saved.id;
        }
      });

      setRows((prev) =>
        prev.map((r) =>
          idByTempId[r.id] ? { ...r, apiId: idByTempId[r.id], isNew: false, isFromUpload: false } : r
        )
      );

      // Refresh all-entries for the totals cards
      ActivityDataService.fetchRows(stageInstanceId, TABLE_KEY)
        .then((all) => setAllEntries(all))
        .catch(() => {});

      const anyRejected = results.some((res) => res.status === "rejected");
      if (anyRejected) {
        setErrorMessage("Some entries failed to save. Please retry submit.");
        return;
      }

      onSubmit();
    } catch (e) {
      console.error(e);
      setErrorMessage("Failed to save entries. Please try again.");
    }
  };

  const summaryKey = useMemo(() => `monthly.report.${reportId}.execSummary`, [reportId]);

  useEffect(() => {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(summaryKey, execSummary);
  }, [execSummary, summaryKey]);


  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <div className="flex-1 overflow-y-auto">
        {/* Summary Title */}
        <div className="text-3xl text-text-dark font-light pb-7.5 p-12">Summary</div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white p-5 mb-6 mx-12 rounded-[var(--radius-3)] shadow-sm">
          <div className="pb-6">
            <div className="text-sm text-text-faint mb-1">Emissions this period</div>
            <div className="text-[28px] font-bold text-text-dark">
              {summaryLoading ? "—" : formatNumber(thisPeriod)}{" "}
              <span className="text-[28px] font-light text-text-dark">
                tCO<sub>2</sub>e
              </span>
            </div>
          </div>
          <div className=" pb-6 md:border-x md:border-neutral-90 md:px-6">
            <div className="text-sm text-text-faint mb-1">Emissions last period</div>
            <div className="text-[28px] font-bold text-text-dark">
              {summaryLoading ? "—" : formatNumber(lastPeriod)}{" "}
              <span className="text-[28px] font-light text-text-dark">
                tCO<sub>2</sub>e
              </span>
            </div>
          </div>

          <div className="pb-6">
            <div className="text-sm text-text-faint mb-1">Total emissions reported</div>
            <div className="text-[28px] font-bold text-text-dark">
              {summaryLoading ? "—" : formatNumber(totalReported)}{" "}
              <span className="text-[28px] font-light text-text-dark">
                tCO<sub>2</sub>e
              </span>
            </div>
          </div>
        </div>

        {/* Monthly Report Data Section */}
        <div className="space-y-6 m-12">
          <div className="text-2xl font-light text-text-dark mb-4">{currentReport}</div>

          <div className="border border-neutral-90 bg-white px-6 pt-6 pb-8 rounded-md">
            <div className="flex items-center justify-between mb-4">
              <div className="text-[20px] text-text-dark flex items-center">
                Materials
                <img src={Help} alt="Help" className="inline-block ml-2 w-4 h-4" />
              </div>

              {/* Accordion Toggle */}
              <button
                type="button"
                onClick={() => setExpanded((x) => !x)}
                aria-expanded={expanded}
                aria-controls="materials-section"
                className="w-5 h-5 inline-flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-primary rounded cursor-pointer"
              >
                <img src={ArrowUp} alt={expanded ? "Collapse" : "Expand"} className="w-5 h-5" />
              </button>
            </div>

            {expanded && (
              <>
                {/* Actions */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end mt-4 mb-5 gap-4">
                  <div className="flex flex-wrap gap-6 text-primary text-sm">
                    <button
                      type="button"
                      // onClick={() =>
                      //   downloadCsv(
                      //     rows,
                      //     `${currentReport ? currentReport.replace(/\s+/g, "_") : "report"}_data.csv`
                      //   )
                      // }

                      onClick={() =>
                        // Option A (Template only — headers only) ← use this if you want empty file with headers
                        downloadCsv(
                          MATERIAL_COLUMNS,
                          [], // no rows
                          `${currentReport ? currentReport.replace(/\s+/g, "_") : "report"}_data.csv`,
                          true, // headerOnly
                          true  // withBom (optional, helps Excel)
                        )
                      }
                      className="flex items-center gap-1 transition-opacity hover:bg-neutral-90 px-0.5 cursor-pointer"
                    >
                      <img src={Download} alt="" className="h-5 w-5" />
                      <span className="font-medium">Download a copy</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleUploadClick}
                      className="flex items-center gap-1  transition-opacity hover:bg-neutral-90 px-0.5 cursor-pointer"
                      disabled={!canEdit}
                    >
                      <img src={UploadFile} alt="" className="h-5 w-5" />
                      <span className="font-medium">Upload file</span>
                    </button>

                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".csv,application/json,text/csv"
                      onChange={handleFileChange}
                      style={{ display: "none" }}
                    />
                    <button
                      type="button"
                      onClick={handleAddRow}
                      className="flex items-center gap-1 transition-opacity hover:bg-neutral-90 px-0.5 cursor-pointer"
                      disabled={!canEdit}
                    >
                      <img src={Add} alt="" className="h-5 w-5" />
                      <span className="font-medium">Add row</span>
                    </button>
                  </div>
                </div>

                {/* Error Message */}
                {errorMessage && (
                  <div className="text-sm text-primary mb-2" role="alert">
                    {errorMessage}
                  </div>
                )}

                {/* Table */}
                <div id="materials-section" className="overflow-x-auto">
                  {/* Header */}
                  <div className="grid grid-cols-7 gap-0 border-collapse border border-neutral-90 p-4 bg-neutral-95 text-base text-text-dark">
                    {[
                      { label: "Emissions sub-category", lock: false },
                      { label: "Emissions source", lock: false },
                      { label: "Unit", lock: false },
                      { label: "Data quality", lock: false },
                      { label: "Quantity (unit)", lock: false },
                      { label: "Emissions (tCO₂e)", lock: true },
                      { label: "Notes / Comments (optional)", lock: false },
                    ].map((h, i) => (
                      <div
                        key={h.label}
                        className={[
                          "h-12 flex items-center text-sm font-medium",
                          i !== 0 ? "border-l border-neutral-90 pl-4" : "",
                        ].join(" ")}
                      >
                        <span className="flex items-start">
                          {h.label}
                          {h.lock && <img src={Lock} alt="Locked" className="ml-2 h-4 w-4" />}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Body */}
                  <div>
                    {rows.map((row) => {
                      return (
                        <div
                          key={row.id}
                          className={[
                            "grid grid-cols-7 gap-0 border-collapse border-b border-neutral-90 last:border-b-0",
                            row.isNew ? "bg-table-row p-4" : "bg-white py-3 px-2",
                          ].join(" ")}
                        >
                          {/* Emissions sub-category */}
                          <div>
                            {row.isNew && !row.isFromUpload ? (
                              <SelectListbox
                                value={row.subCategory}
                                onChange={(v: string) => handleSubcategoryChange(row.id, v)}
                                options={subCategoryOptions}
                                aria-label="Emissions sub-category"
                                placeholder=""
                                disabled={!canEdit || loadingSubcats}
                                className={addInput}
                              />
                            ) : (
                              <div className={readOnlyText}>
                                {row.subCategory ? subcatLabelById[row.subCategory] ?? row.subCategory : ""}
                              </div>
                            )}
                          </div>

                          {/* Emissions source */}
                          <div className="ml-4">
                            {row.isNew && !row.isFromUpload ? (
                              <SelectListbox
                                value={row.source}
                                onChange={(v: string) => handleSourceChangeCascading(row.id, v)}
                                options={sourceOptionsByRow[row.id] ?? []}
                                aria-label="Emissions source"
                                placeholder=""
                                disabled={!canEdit || !row.subCategory || loadingRows[row.id]?.sources}
                                className={addInput}
                              />
                            ) : (
                              <div className={readOnlyText}>{labelForSource(row.id, row.subCategory, row.source)}</div>
                            )}
                          </div>

                          {/* Unit */}
                          <div className="ml-4">
                            {(row.isNew && !row.isFromUpload) || editingCell[row.id]?.unit ? (
                              <SelectListbox
                                value={row.unit}
                                onChange={(v: string) => handleChange(row.id, "unit")({ target: { value: v } })}
                                onBlur={() => stopEdit(row.id, "unit")}
                                options={unitOptionsByRow[row.id] ?? []}
                                aria-label="Unit"
                                placeholder=""
                                disabled={!canEdit || !row.source || loadingRows[row.id]?.units}
                                className={addInput}
                                autoFocus={!!editingCell[row.id]?.unit}
                              />
                            ) : (
                              <div
                                className={borderlessText}
                                onDoubleClick={() => startEdit(row.id, "unit")}
                                role="button"
                                tabIndex={0}
                                title="Double-click to edit"
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") startEdit(row.id, "unit");
                                }}
                              >
                                {labelForUnit(row.id, row.source, row.unit)}
                              </div>
                            )}
                          </div>

                          {/* Data quality */}
                          <div className="ml-4">
                            {(row.isNew && !row.isFromUpload) || editingCell[row.id]?.dataQuality ? (
                              <SelectListbox
                                value={row.dataQuality}
                                onChange={(v: string) => handleChange(row.id, "dataQuality")({ target: { value: v } })}
                                options={dataQualityOptionsFormatted}
                                onBlur={() => stopEdit(row.id, "dataQuality")}
                                aria-label="Data quality"
                                placeholder=""
                                className={addInput}
                                autoFocus={!!editingCell[row.id]?.dataQuality}
                                disabled={!canEdit}
                              />
                            ) : (
                              <div
                                className={borderlessText}
                                onDoubleClick={() => startEdit(row.id, "dataQuality")}
                                role="button"
                                tabIndex={0}
                                title="Double-click to edit"
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") startEdit(row.id, "dataQuality");
                                }}
                              >
                                {row.dataQuality || ""}
                              </div>
                            )}
                          </div>

                          {/* Quantity (unit) */}
                          <div className="ml-4">
                            {(row.isNew && !row.isFromUpload) || editingCell[row.id]?.quantity ? (
                              <NumericInput
                                value={row.quantity ?? ""}
                                onChange={handleChange(row.id, "quantity")}
                                onBlur={() => stopEdit(row.id, "quantity")}
                                className={addInput}
                                placeholder=""
                                autoFocus={!!editingCell[row.id]?.quantity}
                                disabled={!canEdit}
                              />
                            ) : (
                              <div
                                className={borderlessText}
                                onDoubleClick={() => startEdit(row.id, "quantity")}
                                role="button"
                                tabIndex={0}
                                title="Double-click to edit"
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") startEdit(row.id, "quantity");
                                }}
                              >
                                {row.quantity ?? ""}
                              </div>
                            )}
                          </div>

                          {/* Emissions (tCO2e) — read-only */}
                          <div className="ml-4">
                            <div
                              className={readOnlyText}
                              aria-live="polite"
                              aria-busy={!!emissionsLoadingByRow[row.id]}
                            >
                              {emissionsLoadingByRow[row.id] ? "…" : row.emissions || ""}
                            </div>
                          </div>

                          {/* Notes */}
                          <div className="ml-4">
                            {(row.isNew && !row.isFromUpload) || editingCell[row.id]?.notes ? (
                              <input
                                type="text"
                                value={row.notes ?? ""}
                                onChange={handleChange(row.id, "notes")}
                                onBlur={() => stopEdit(row.id, "notes")}
                                className={addInput}
                                aria-label="Notes"
                                maxLength={30}
                                autoFocus={!!editingCell[row.id]?.notes}
                                disabled={!canEdit}
                              />
                            ) : (
                              <div
                                className={borderlessText}
                                onDoubleClick={() => startEdit(row.id, "notes")}
                                role="button"
                                tabIndex={0}
                                title="Double-click to edit"
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") startEdit(row.id, "notes");
                                }}
                              >
                                {row.notes || ""}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Executive Summary */}
          <div className="border border-neutral-90 bg-white p-6 rounded-[var(--radius-3)]">
            <div className="mb-2">
              <label className="text-sm text-text-base font-medium">
                Executive summary <span className="font-normal">(optional)</span>
              </label>
              <div className="text-xs text-text-faint">{charCount}/{charLimit}</div>
            </div>
            <textarea
              className="border border-border-input w-full rounded-[var(--radius-3)] h-32 p-3 outline-none focus:ring-2 focus:ring-border-input focus:border-transparent"
              value={execSummary}
              onChange={(e) => setExecSummary(e.target.value.slice(0, charLimit))}
              maxLength={charLimit}
              aria-label="Executive summary"
              disabled={!canEdit}
            />
          </div>
        </div>
      </div>
      {/* Footer actions: Submit / Approve */}
      <div className="bg-white p-5 px-12 flex justify-end shrink-0">
        {canEdit && reportStatus === "In Progress" && (
          <button
            onClick={handleLocalSubmit}
            title="Submit"
            className="bg-primary text-white px-6 py-3 rounded-[var(--radius-3)] text-sm font-medium hover:bg-opacity-90 transition-colors cursor-pointer"
          >
            Submit
          </button>
        )}
        {canApprove && (
          <button
            onClick={() => onApprove(thisPeriod)}
            title="Approve"
            className="bg-success text-white px-6 py-3 rounded-[var(--radius-3)] text-sm font-medium hover:bg-opacity-90 transition-colors cursor-pointer"
          >
            Approve
          </button>
        )}
      </div>
    </div>
  );
};

export default ReportData;