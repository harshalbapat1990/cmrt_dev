export type ParsedRow = Record<string, unknown>;

export const parseCsvText = (text: string): string[][] => {
  const rows: string[][] = [];
  let cur = "";
  let row: string[] = [];
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (ch === '"') {
      if (inQuotes && next === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (ch === "," && !inQuotes) {
      row.push(cur);
      cur = "";
      continue;
    }

    if ((ch === "\n" || ch === "\r") && !inQuotes) {
      row.push(cur);
      rows.push(row);
      cur = "";
      row = [];
      if (ch === "\r" && next === "\n") i++;
      continue;
    }

    cur += ch;
  }

  if (cur !== "" || row.length > 0) {
    row.push(cur);
    rows.push(row);
  }

  return rows.filter(r => !(r.length === 1 && r[0] === ""));
};

export type UploadOptions = {
  normalizeHeader?: (headerLabel: string) => string;

  columns?: { key: string; label: string }[];

  numericKeys?: string[];
};

/**
 * Parses CSV or JSON file into array of objects.
 * Caller MUST provide header→key mapping via normalizeHeader OR columns.
 */
export const uploadCsv = async (file: File, options: UploadOptions): Promise<ParsedRow[]> => {
  const text = await file.text();
  const filename = file.name.toLowerCase();

  // JSON case
  if (filename.endsWith(".json")) {
    try {
      const parsed = JSON.parse(text);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  // CSV case
  const rows = parseCsvText(text);
  if (rows.length === 0) return [];

  const headerRow = rows[0].map(h => h.trim());

  if (!options.normalizeHeader && !options.columns) {
    throw new Error("uploadCsv: Provide either normalizeHeader or columns[] for header mapping.");
  }

  const normalizeHeader =
    options.normalizeHeader ||
    ((label: string) => {
      const found = options.columns!.find(c => c.label.trim() === label.trim());
      return found ? found.key : "";
    });

  const numericKeys = new Set(options.numericKeys ?? []);

  const keys = headerRow.map(normalizeHeader);
  const out: ParsedRow[] = [];

  for (let i = 1; i < rows.length; i++) {
    const cells = rows[i];
    const obj: ParsedRow = {};

    for (let j = 0; j < keys.length; j++) {
      const key = keys[j];
      if (!key) continue;

      const raw = (cells[j] ?? "").trim();

      if (numericKeys.has(key)) {
        const n = raw === "" ? undefined : Number(raw.replace(/,/g, ""));
        obj[key] = Number.isNaN(n) ? raw : n;
      } else {
        obj[key] = raw;
      }
    }

    if (!obj.id) {
      obj.id = `row-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
    }

    out.push(obj);
  }

  return out;
};