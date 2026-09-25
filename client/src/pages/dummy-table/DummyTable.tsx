import React, {
  useEffect,
  useState,
  useCallback,
  useMemo,
} from "react";
import Table from "../../components/common/Table";
// import EmissionEntriesService from "../../services/EmissionEntries.service";
import DummyTableJson from "./DummyTableData.json";
import LookupService from "../../services/Lookups.service";
import { NumericInput } from "../../components/common/NumericInput";
import { UploadModal } from "./UploadModal";
import * as XLSX from "xlsx";

const MATERIAL_COLUMNS: { key: string; label: string }[] = [
  { key: "subCategory", label: "Emissions sub-category" },
  { key: "source", label: "Emissions source" },
  { key: "unit", label: "Unit" },
  { key: "dataQuality", label: "Data quality" },
  { key: "quantity", label: "Quantity (unit)" },
  { key: "emissions", label: "Emissions (tCO2e)" },
  { key: "notes", label: "Notes / Comments (optional)" },
];

const DATA_QUALITY_OPTIONS = [
  { label: "Estimated", value: "Estimated" },
  { label: "Monitored", value: "Monitored" },
];

const FILE_HEADERS: any = MATERIAL_COLUMNS.map((col) => ({
  key: col.key,
  label: col.label,
}));

const DummyTable: React.FC = () => {
  const [rows, setRows] = useState<any[]>([]); // table rows
  const [subCategoryOptions, setSubCategoryOptions] = useState<any[]>([]);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  useEffect(() => {
    // Simulate fetching data
    const fetchData = async () => {
      // Simulate a delay
      // const response = await EmissionEntriesService.fetchEmissionDetails();
      // Here you would normally fetch data from an API and set it to state
      const response = DummyTableJson; // Using local JSON data for simulation
      if (response.length > 0) {
        setRows(
          response.map((r) => ({
            id: crypto.randomUUID(),
            subCategoryId: r.emissions_sub_category_id,
            subCategory: r.emissions_sub_category_name,
            sourceId: r.emissions_source_id,
            source: r.emissions_source_name,
            unitId: r.measurement_unit_id,
            unit: r.measurement_unit_name,
            dataQuality: r.data_quality,
            quantity: r.quantity,
            emissions: r.emissions_tco2e,
            notes: r.notes,
          })),
        ); //set response to rows to display in table
      }
    };
    fetchData();
  }, []);

  const LookupsAdapter = {
    fetchSubcategories: async () => {
      const list = await LookupService.fetchSubCategories();
      return list;
    },
    fetchSources: async (subCategoryId: string) => {
      return await LookupService.fetchSources(String(subCategoryId));
    },
    fetchUnits: async () => {
      try {
        const u = await LookupService.fetchUnits();
        return u;
      } catch (e) {
        console.error('[DummyTable] fetchUnits failed, retrying once:', e);
        return await LookupService.fetchUnits(); 
      }
    },
  };

  const validateAndNormalizeUpload = async (parsedRows: any[]) => {
    const { validateUploadedRows } = await import("./validation");
    const { validRows, errors } = await validateUploadedRows(
      parsedRows,
      LookupsAdapter as any,
      DATA_QUALITY_OPTIONS,
    );
    return { validRows, errors };
  };

  const replaceRowsAndPersist = async (validRows: any[]) => {
    setRows(
      validRows.map((r: any) => ({
        id: crypto.randomUUID(),
        subCategoryId: String(r.subCategoryId),
        subCategory: String(r.subCategory),
        sourceId: String(r.sourceId),
        source: String(r.source),
        unitId: String(r.unitId),
        unit: String(r.unit),
        dataQuality: String(r.dataQuality),
        quantity: normalizeQty(r.quantity),
        emissions: r.emissions ?? "",
        notes: String(r.notes ?? ""),
      })),
    );
  };

  const normalizeQty = (v: any) => {
    if (v === "" || v == null) return null;
    const n = typeof v === "number" ? v : Number(String(v).trim());
    return Number.isFinite(n) ? n : null;
  };

  const ensureSubcategoriesLoaded = useCallback(async () => {
    if (subCategoryOptions.length) return;
    try {
      const list = await LookupService.fetchSubCategories();
      const opts = list.map((s: any) => ({
        label: s.name ?? s.sub_category_name ?? String(s.emissions_category_id),
        value: String(s.emissions_category_id),
      }));

      setSubCategoryOptions(opts);
    } catch (e) {
      console.error(e);
    }
  }, [subCategoryOptions.length]);

  useEffect(() => {
    ensureSubcategoriesLoaded();
  }, []);

  const fetchSourceOptions = useCallback(
    async ({ row }: { row: any; isNew: boolean }): Promise<any> => {
      const scId = row?.subCategoryId;
      if (!scId) return [];

      try {
        const list = await LookupService.fetchSources(String(scId));
        const opts: any = (list || []).map((s: any) => ({
          label: s.name ?? s.source_name ?? String(s.id),
          value: String(s.id),
        }));
        return opts;
      } catch (e) {
        console.error(e);
        return [];
      }
    },
    [subCategoryOptions],
  );

  // enables Table to cascade updates across fields in one go
  const onRowPatch = ({
    id,
    patch,
  }: {
    id: unknown;
    patch: Partial<any>;
    item: any;
  }) => {
    if (typeof id !== "string") return;
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  // Single-cell change - used by number/text editors
  const onCellChange = ({
    id,
    key,
    value,
  }: {
    id: string;
    key: any;
    value: any;
  }) => {
    setRows((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        if (key === "dataQuality") {
          return { ...r, dataQuality: String(value ?? "") };
        }
        if (key === "quantity") {
          return { ...r, quantity: normalizeQty(value) };
        }
        if (key === "notes") {
          return { ...r, notes: String(value ?? "") };
        }
        return { ...r, [key]: value };
      }),
    );
  };

  const columns = useMemo(() => {
    return [
      {
        header: "Emissions sub-category",
        key: "subCategory",
        editable: (row: any) => row.id === "__NEW__",
        editorType: "select",
        idKey: "subCategoryId",
        getOptions: async () => subCategoryOptions,
        clearsOnChange: ["source", "sourceId", "unit", "unitId"],
      },
      {
        header: "Emissions source",
        key: "source",
        editable: (row: any) => row.id === "__NEW__",
        editorType: "select",
        idKey: "sourceId",
        dependsOnKeys: ["subCategoryId"],
        getOptions: fetchSourceOptions,
        clearsOnChange: ["unit", "unitId"],
        noCache: true,
        refreshOnDepsChange: true,
      },
      {
        header: "Unit",
        key: "unit",
        editable: true,
        editorType: "select",
        idKey: "unitId",
        // dependsOnKeys: ["sourceId"],
        getOptions: async () => {
          // const sourceId = row?.sourceId;
          // if (!sourceId) return [];
          const u: any = await LookupService.fetchUnits();
          const arr = Array.isArray(u) ? u : u ? [u] : [];
          return arr
            .map((x: any) => ({
              label: x?.name ?? x?.unit_name ?? "",
              value: String(x?.id ?? x?.unit_id ?? ""),
            }))
            .filter((o: any) => o.label && o.value);
        },
      },
      {
        header: "Data quality",
        key: "dataQuality",
        editable: true,
        editorType: "select",
        idKey: undefined,
        getOptions: () => DATA_QUALITY_OPTIONS,
      },
      {
        header: "Quantity (unit)",
        key: "quantity" as const,
        editable: true,
        renderEditor: ({ value, onChange, onCommit }: any) => (
          <NumericInput
            value={value}
            onChange={(val) => onChange(val)}
            onCommit={(val) => onCommit(val)}
            allowDecimal={true}
            autoFocus
            uncontrolled={true}
          />
        ),
      },

      { header: "Emissions (tCO2e)", key: "emissions", editable: false },
      {
        header: "Notes / Comments (optional)",
        key: "notes",
        editable: true, // default editor is input[type=text]
      },
    ];
  }, [subCategoryOptions, fetchSourceOptions]);

  const newRowInitial = () => ({
    subCategory: "",
    subCategoryId: "",
    source: "",
    sourceId: "",
    unit: "",
    unitId: "",
    dataQuality: "",
    quantity: null,
    emissions: "",
    notes: "",
  });

  const onNewRowSave = async (draft: Partial<any>) => {
    const requiredFields = [
      "subCategoryId",
      "sourceId",
      "unitId",
      "dataQuality",
      "quantity",
    ];
    const missing = requiredFields.filter((key) => {
      const v = draft[key];
      return v === "" || v === null || v === undefined;
    });

    if (missing.length > 0) {
      setErrorMessage("Please enter the required fields.");
      return false; //  Don't save the row
    }
    setErrorMessage(null);

    const row: any = {
      id: crypto.randomUUID(),
      subCategory: draft.subCategory ?? "",
      subCategoryId: draft.subCategoryId ?? "",
      source: draft.source ?? "",
      sourceId: draft.sourceId ?? "",
      unit: draft.unit ?? "",
      unitId: draft.unitId ?? "",
      dataQuality: draft.dataQuality ?? "",
      quantity: normalizeQty((draft as any).quantity),
      emissions: draft.emissions ?? "", 
      notes: draft.notes ?? "",
    };
    setRows((prev) => [row, ...prev]);

    return true;
  };

  const parseFileToRows = async (file: File): Promise<any[]> => {
    const name = file.name.toLowerCase();
    if (name.endsWith(".csv")) {
      const { uploadCsv } = await import("../../utils/uploadCsv");
      const rows = await uploadCsv(file, {
        columns: FILE_HEADERS.map((h: any) => ({ key: h.key, label: h.label })),
        numericKeys: ["quantity"],
      });
      return rows as any[];
    }

    // .xlsx path
    const data = await file.arrayBuffer();
    const wb = XLSX.read(data, { type: "array" });
    const ws = wb.Sheets[wb.SheetNames[0]];
    const aoa = XLSX.utils.sheet_to_json<string[]>({
      raw: false,
      header: 1,
      defval: "",
      range: 0,
      sheet: ws,
    } as any) as string[][];

    if (!aoa || !aoa.length) return [];

    // header normalization based on FILE_HEADERS labels
    const headers = aoa[0].map((h) => String(h || "").trim());
    const labelToKey = new Map<string, string>(
      FILE_HEADERS.map((c: any) => [c.label.trim(), c.key]),
    );
    const keys = headers.map((label) => labelToKey.get(label) || "");

    const out: any[] = [];
    for (let i = 1; i < aoa.length; i++) {
      const row = aoa[i] || [];
      const obj: any = {};
      for (let j = 0; j < keys.length; j++) {
        const key = keys[j];
        if (!key) continue;
        let val = (row[j] ?? "").toString().trim();
        if (key === "quantity") {
          const n = val === "" ? undefined : Number(val.replace(/,/g, ""));
          obj[key] = Number.isFinite(n) ? n : val; // keep raw if NaN; validator will flag it
        } else {
          obj[key] = val;
        }
      }
      if (!obj.id)
        obj.id = `row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      out.push(obj);
    }
    return out;
  };

  return (
    <>
      {showUploadModal && (
        <UploadModal
          open={showUploadModal}
          onClose={() => setShowUploadModal(false)}
          parseFile={parseFileToRows}
          validateRows={validateAndNormalizeUpload}
          onSuccess={replaceRowsAndPersist}
        />
      )}
      <div className="p-4">
        <h2 className="text-2xl font-bold mb-4">Dummy Table</h2>
        {errorMessage && (
          <div className="mb-3 px-4 py-2 text-sm text-danger bg-red-100 border border-red-300 rounded">
            {errorMessage}
          </div>
        )}
        <Table
          data={rows}
          columns={columns as any}
          onCellChange={({ id, key, value }) => {
            if (typeof id === "string") {
              onCellChange({ id, key, value });
            }
          }}
          onRowPatch={onRowPatch as any}
          enableInlineNewRow
          newRowInitial={newRowInitial}
          onNewRowSave={onNewRowSave}
          exportFileName="Emission-Entries.csv"
          onRequestUpload={() => setShowUploadModal(true)}
        />
        {/* {loading && <div className="mt-4 text-sm text-gray-500">Loading…</div>} */}
      </div>
    </>
  );
};

export default DummyTable;
