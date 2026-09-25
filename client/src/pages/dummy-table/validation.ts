import type { ParsedRow } from "../../utils/uploadCsv";

type DataQualityOption = { label: string; value: string };

type LookupService = {
  fetchSubcategories: () => Promise<any[]>;
  fetchSources: (subCategoryId: string) => Promise<any[]>;
  fetchUnits: () => Promise<any[] | any>;
};

type ValidatedRow = {
  subCategory: string;
  subCategoryId: string;
  source: string;
  sourceId: string;
  unit: string;
  unitId: string;
  dataQuality: string;
  quantity: number | null;
  emissions?: number | string;
  notes?: string;
};

export const validateUploadedRows = async (
  parsedRows: ParsedRow[],
  LookupService: LookupService,
  dataQualityOptions: DataQualityOption[]
): Promise<{ validRows: ValidatedRow[]; errors: string[] }> => {
  const errors: string[] = [];
  const validRows: ValidatedRow[] = [];

  const subCats = await LookupService.fetchSubcategories();

  const subcatByLabel = new Map<string, { id: string; name: string }>();
  const subcatById = new Map<string, { id: string; name: string }>();
  (subCats || []).forEach((s: any) => {
    const id = String(s.id ?? s.sub_category_id ?? "");
    const name = String(s.name ?? s.sub_category_name ?? "");
    if (id && name) {
      subcatByLabel.set(name.toLowerCase(), { id, name });
      subcatById.set(id, { id, name });
    }
  });

  const dqSet = new Set(dataQualityOptions.map(o => o.value.toLowerCase()));

  const uniqueSubcatLabels = new Set<string>();
  const needSourcesForSubcatId = new Set<string>();

  parsedRows.forEach((row) => {
    const scLabel = String(row["subCategory"] ?? "").trim();
    if (scLabel) uniqueSubcatLabels.add(scLabel.toLowerCase());
  });

  const subcatLabelToId = new Map<string, string>();
  for (const label of uniqueSubcatLabels) {
    const sc = subcatByLabel.get(label);
    if (!sc) continue;
    subcatLabelToId.set(label, sc.id);
    needSourcesForSubcatId.add(sc.id);
  }

  const sourceIndexBySubcatId = new Map<string, Map<string, { id: string; name: string }>>();
  await Promise.all(
    Array.from(needSourcesForSubcatId).map(async (scId) => {
      const sources = await LookupService.fetchSources(scId);
      const m = new Map<string, { id: string; name: string }>();
      (sources || []).forEach((s: any) => {
        const id = String(s.id ?? s.source_id ?? "");
        const name = String(s.name ?? s.source_name ?? "");
        if (id && name) m.set(name.toLowerCase(), { id, name });
      });
      sourceIndexBySubcatId.set(scId, m);
    })
  );

  const unitsBySourceId = new Map<string, Map<string, { id: string; name: string }>>();

  const ensureUnitsForSource = async (srcId: string) => {
    const u = await LookupService.fetchUnits();
    const arr = Array.isArray(u) ? u : (u ? [u] : []);
    const m = new Map<string, { id: string; name: string }>();
    arr.forEach((x: any) => {
      const id = String(x?.id ?? x?.unit_id ?? "");
      const name = String(x?.name ?? x?.unit_name ?? "");
      if (id && name) m.set(name.toLowerCase(), { id, name });
    });
    unitsBySourceId.set(srcId, m);
  };

  parsedRows.forEach((row, idx) => {
    const rowNum = idx + 2; // 1-based + header
    const scLabel = String(row["subCategory"] ?? "").trim();
    const srcLabel = String(row["source"] ?? "").trim();
    const unitLabel = String(row["unit"] ?? "").trim();
    const dq = String(row["dataQuality"] ?? "").trim();
    const quantityRaw = row["quantity"];
    const notes = String(row["notes"] ?? "");
    const emissions = row["emissions"];

    if (!scLabel) errors.push(`Row ${rowNum}: Missing "Emissions sub-category"`);
    if (!srcLabel) errors.push(`Row ${rowNum}: Missing "Emissions source"`);
    if (!unitLabel) errors.push(`Row ${rowNum}: Missing "Unit"`);

    // Data quality
    if (!dq || !dqSet.has(dq.toLowerCase())) {
      errors.push(`Row ${rowNum}: Invalid "Data quality": "${dq}"`);
    }

    // Quantity numeric (allow empty -> null)
    let quantity: number | null = null;
    if (quantityRaw !== undefined && quantityRaw !== "") {
      const n = typeof quantityRaw === "number" ? quantityRaw : Number(String(quantityRaw).replace(/,/g, ""));
      if (!Number.isFinite(n)) {
        errors.push(`Row ${rowNum}: "Quantity" must be numeric`);
      } else {
        quantity = n;
      }
    }

    // Subcategory lookup
    const scId = subcatLabelToId.get(scLabel.toLowerCase());
    if (!scId) {
      errors.push(`Row ${rowNum}: Unknown sub-category "${scLabel}"`);
      return; // skip further validations dependent on scId
    }

    const sourceMap = sourceIndexBySubcatId.get(scId) || new Map<string, { id: string; name: string }>();
    const sourceHit = sourceMap.get(srcLabel.toLowerCase());
    if (!sourceHit) {
      errors.push(`Row ${rowNum}: Unknown source "${srcLabel}" for sub-category "${scLabel}"`);
      return; // skip unit check
    }

    // Units for that source
    const srcId = sourceHit.id;
    // eslint-disable-next-line no-async-promise-executor
    // We'll resolve sequentially since this is inside sync loop; we’ll collect promises and await later
    (async () => await ensureUnitsForSource(srcId))();
    validRows.push({
      subCategory: scLabel,
      subCategoryId: scId,
      source: srcLabel,
      sourceId: srcId,
      unit: unitLabel, // check later once units fetched
      unitId: "",      // fill later
      dataQuality: dq,
      quantity,
      emissions: emissions as any,
      notes,
    });
  });

  // Wait to ensure units are fetched (sequential async runners kicked earlier)
  // In strict types, better to fetch units in one pass first, but this is OK for moderate files.
  await Promise.all(
    Array.from(new Set(validRows.map(r => r.sourceId))).map(srcId => ensureUnitsForSource(srcId))
  );

  // Now check unit validity & fill unitId
  validRows.forEach((r, idx) => {
    const rowNum = idx + 2;
    const uMap = unitsBySourceId.get(r.sourceId) || new Map<string, { id: string; name: string }>();
    const unitHit = uMap.get(r.unit.toLowerCase());
    if (!unitHit) {
      errors.push(`Row ${rowNum}: Unknown unit "${r.unit}" for source "${r.source}"`);
    } else {
      r.unitId = unitHit.id;
      r.unit = unitHit.name;
    }
  });

  return { validRows, errors };
};