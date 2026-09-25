import * as XLSX from "xlsx";

export type FileHeader = { key: string; label: string };

export async function parseFileToRows(
  file: File,
  headers: FileHeader[],
  numericKeys: string[] = [],
  options: any={},
): Promise<any[]> {
  const name = file.name.toLowerCase();

  
const defaultNormalize = (str: string) =>
    String(str || "")
      .toLowerCase()
      .replace(/[^a-z0-9]/g, "");

  const norm = options.normalizeHeader || defaultNormalize;

  const labelToKey = new Map<string, string>();
  headers.forEach(h => {
    const normalizedLabel = norm(h.label);
    const normalizedKey = norm(h.key);
    
    labelToKey.set(normalizedLabel, h.key);
    labelToKey.set(normalizedKey, h.key);

    // If label contains parentheses, map the text before it (e.g., "Quantity" from "Quantity (unit)")
    if (h.label.includes("(")) {
      const prefix = norm(h.label.split("(")[0]);
      if (prefix) labelToKey.set(prefix, h.key);
    }
    
     if (normalizedLabel.includes("emissions")) {
      labelToKey.set(normalizedLabel.replace("emissions", "emission"), h.key);
    } else if (normalizedLabel.includes("emission")) {
      labelToKey.set(normalizedLabel.replace("emission", "emissions"), h.key);
    }

    if (normalizedKey.includes("emissions")) {
      labelToKey.set(normalizedKey.replace("emissions", "emission"), h.key);
    }

    // Hardcode safety nets for common "notes" variations
    if (h.key === "notes") {
       labelToKey.set("notes", "notes");
        labelToKey.set("comments", "notes");
        labelToKey.set("notescomments", "notes"); // Matches "Notes/Comments" or "Notes / Comments"
        labelToKey.set("notescommentsoptional", "notes");
    }

    if (h.key === "emissions_source_name" || h.key === "emissions_source") {
       labelToKey.set("source", h.key);
       labelToKey.set("emissionsource", h.key); // Handles "Emission source"
    }
    
    if (h.key === "emissions_category") {
       labelToKey.set("category", h.key);
       labelToKey.set("emissioncategory", h.key);
    }
    
    if (h.key === "emissions_subcategory") {
       labelToKey.set("subcategory", h.key);
       labelToKey.set("emissionsubcategory", h.key);
    }
  });

  if (name.endsWith(".csv")) {
    const { uploadCsv } = await import("./uploadCsv");
    //  const labelToKey = new Map(headers.map(h => [norm(h.label.trim()), h.key]));
    const rows = await uploadCsv(file, {
      columns: headers.map(h => ({ key: h.key, label: h.label })),
      numericKeys,
      normalizeHeader: (label: string) => {
        return labelToKey.get(norm(label)) || "";
      },
    });
    return rows as any[];
  }

  // XLSX path
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

  const fileHeaderRow = aoa[0].map(h => String(h || ""));


  // Build lookup → find each file header label → map to internal key
  // const labelToKey = new Map(headers.map(h => [norm(h.label.trim()), h.key]));
  const keys = fileHeaderRow.map(label => labelToKey.get(norm(label)) || "");

  const out: any[] = [];

  for (let i = 1; i < aoa.length; i++) {
    const row = aoa[i] || [];
    const obj: any = {};

    for (let j = 0; j < keys.length; j++) {
      const key = keys[j];
      if (!key) continue;

      let val = (row[j] ?? "").toString().trim();

      // Numeric column?
      if (numericKeys.includes(key)) {
        const n = val === "" ? undefined : Number(val.replace(/,/g, ""));
        obj[key] = Number.isFinite(n) ? n : val;
      } else {
        obj[key] = val;
      }
    }

    if (!obj.id)
      obj.id = `row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    out.push(obj);
  }

  return out;
}