export type CsvColumn = {
  key: string;       
  label: string;      
  format?: (value: unknown, row: any) => string;
};

/** Escape cell content for CSV */
const escapeCell = (value: unknown): string => {
  const s = String(value ?? "");
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

/** Build header row */
const buildHeader = (columns: CsvColumn[]): string =>
  columns.map(c => escapeCell(c.label)).join(",");

/** Build CSV rows */
const buildRows = (columns: CsvColumn[], rows: any[]): string[] =>
  rows.map(row =>
    columns
      .map(col => {
        const raw = row[col.key];
        const formatted = col.format ? col.format(raw, row) : raw;
        return escapeCell(formatted);
      })
      .join(",")
  );

/**
 * Download CSV file.
 * If rows are empty OR headerOnly=true → only headers are downloaded.
 */
export const downloadCsv = (
  columns: CsvColumn[],
  rows: any[] = [],
  filename = "data.csv",
  headerOnly?: boolean,
  withBom?: boolean
) => {
  const isTemplate = headerOnly || rows.length === 0;

  const header = buildHeader(columns);
  const body = isTemplate ? [] : buildRows(columns, rows);

  const csv = [header, ...body].join("\r\n");
  const finalText = withBom ? `\uFEFF${csv}` : csv;

  const blob = new Blob([finalText], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  URL.revokeObjectURL(url);
};