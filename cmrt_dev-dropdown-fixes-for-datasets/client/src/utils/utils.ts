export const getUniqueValues = (data: any[], key: string): string[] => {
    const uniqueValues = new Set<string>();
    data.forEach(item => {
        if (item[key]) {
            uniqueValues.add(item[key]);
        }
    });
    return Array.from(uniqueValues);
};

/**
 * Safely extracts a human-readable error message from a FastAPI error response.
 * FastAPI 422 Unprocessable Entity responses return `detail` as an array of
 * `{type, loc, msg, input}` objects rather than a plain string. Passing such an
 * array directly as a React child crashes with "Objects are not valid as a React child".
 *
 * Usage: extractApiError(err, 'Operation failed')
 */
export const extractApiError = (err: unknown, fallback: string): string => {
  const detail = (err as any)?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg ?? JSON.stringify(d)).join('; ');
  }
  return fallback;
};


 
// Round a number to exactly 2 decimals, keeping it as a number
export const formatNumber = (n: number | undefined): number => {
  const num = Number(n);
  if (!Number.isFinite(num)) return 0;
  return Math.round((num + Number.EPSILON) * 100) / 100;
};

/** Accepts: "January 2026" or "Jan 2026" 
 * Returns: "2026-01"
*/
export const monthLabelToKey = (label: string): string => {
  const parts = label.trim().split(/\s+/);
  if (parts.length < 2) return "";
  const [mName, yStr] = [parts[0], parts[1]];
  const year = Number(yStr);
  if (!Number.isFinite(year)) return "";

  const months = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
  ];

  const longIdx = months.indexOf(mName.toLowerCase());
  const shortIdx = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    .indexOf(mName.slice(0, 3).toLowerCase());

  const idx = longIdx >= 0 ? longIdx : shortIdx;
  if (idx < 0) return "";

  return `${year}-${String(idx + 1).padStart(2, "0")}`;
};

/**
 * convert any number like value to a reliable number
 */
export const toNumberSafe = (v: string | number | null | undefined): number => {
  const n = typeof v === 'number' ? v : parseFloat(String(v ?? '0'));
  return Number.isFinite(n) ? n : 0;
};

// Using UTC so we don’t get timezone slippage between client locales
export const monthKeyFromDateStrUTC = (iso: string | null): string | "" => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
};

type FormatDisplayOptions = {
  threshold?: number;             // default 1000
  decimalsBelowThreshold?: number; // default 1
  locale?: string;                // default "en-US"
  emptyText?: string;             // default "-"
};

export function formatDisplayNumber(
  input: unknown,
  opts: FormatDisplayOptions = {}
): string {
  const {
    threshold = 1000,
    decimalsBelowThreshold = 1,
    locale = "en-US",
    emptyText = "-",
  } = opts;

  if (input === "" || input == null || input === emptyText) return emptyText;

  // allow "1,234.5"
  const cleaned =
    typeof input === "string" ? input.replace(/,/g, "").trim() : input;

  const n = Number(cleaned);
  if (!Number.isFinite(n)) return emptyText;

  const abs = Math.abs(n);

  if (abs > 0 && abs < 0.001) {
    return n.toExponential(1);
  }

  if (abs > 0 && abs < 1) {
    return new Intl.NumberFormat(locale, {
      useGrouping: false,
      minimumFractionDigits: 0,
      maximumFractionDigits: 3,
    }).format(n);
  }

  const pow = Math.pow(10, decimalsBelowThreshold);
  const rounded1dp = Math.round(n * pow) / pow;

  if (Math.abs(rounded1dp) >= threshold) {
    const asInt = Math.round(rounded1dp);
    return new Intl.NumberFormat(locale, {
      useGrouping: true,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(asInt);
  }

  return new Intl.NumberFormat(locale, {
    useGrouping: false,
    minimumFractionDigits: decimalsBelowThreshold,
    maximumFractionDigits: decimalsBelowThreshold,
  }).format(rounded1dp);
}

/** Convenience wrapper for emissions + quantity */
export const formatEmissionsOrQuantity = (v: unknown, locale = "en-US") =>
  formatDisplayNumber(v, {
    threshold: 1000,
    decimalsBelowThreshold: 1,
    locale,
  });