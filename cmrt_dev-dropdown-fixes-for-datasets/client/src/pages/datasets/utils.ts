import { METRIC_LABEL } from './constants';

export function distinct(arr: string[]): string[] {
  return [...new Set(arr)].sort((a, b) => a.localeCompare(b));
}

export function fmtVal(v: number | null | undefined): string {
  if (v == null) return '—';
  if (v === 0) return '0';
  const s = parseFloat(v.toPrecision(6)).toString();
  return s;
}

export function toNum(v: string | null | undefined): number | null {
  if (v == null || v === '') return null;
  const n = parseFloat(v);
  return isNaN(n) ? null : n;
}

export const LABEL_TO_METRIC_CODE: Record<string, string> = Object.fromEntries(
  Object.entries(METRIC_LABEL).map(([code, label]) => [label, code])
);
