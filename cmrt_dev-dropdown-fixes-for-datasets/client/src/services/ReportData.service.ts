import BaseService from './base.service';

const CACHE_EXPIRATION = 10 * 60 * 1000;

export type EmissionApiRow = {
  a1_3: string | number | null;
  a4: string | number | null;
  a5: string | number | null;
  b2_5?: string | number | null;
  c2?: string | number | null;
  c3_4?: string | number | null;
};

type CacheEntry<T> = {
  data: T | null;
  timestamp: number;
  cacheDurationMs: number;
};

function isFresh(entry?: CacheEntry<any>): boolean {
  if (!entry || entry.data === null || entry.data === undefined) return false;
  return Date.now() - entry.timestamp < entry.cacheDurationMs;
}

function nowEntry<T>(data: T): CacheEntry<T> {
  return {
    data,
    timestamp: Date.now(),
    cacheDurationMs: CACHE_EXPIRATION,
  };
}

function toNumberSafe(v: string | number | null | undefined): number {
  const n = typeof v === 'number' ? v : parseFloat(String(v ?? '0'));
  return Number.isFinite(n) ? n : 0;
}

function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export class ReportDataService extends BaseService {
  constructor() {
    super('/api/views/emission-factor-values-pivot');
  }

  private totalsCache: Record<string, CacheEntry<number>> = {};

  private cacheKey(subcategoryId: string, sourceId: string, unitId: string): string {
    return `${subcategoryId}|${sourceId}|${unitId}`;
  }

  private async safeGet<T = any>(path: string): Promise<T> {
    try {
      const response = await this.get(path);
      const data = response?.data;
      if (!Array.isArray(data)) {
        throw new Error(`Expected array but received ${typeof data} at '${path}'`);
      }
      return data as T;
    } catch (error: any) {
      console.error(`ReportDataService GET ${path} failed:`, error?.message ?? error);
      throw error;
    }
  }

  async fetchEmissionValues(
    subcategoryId: string,
    sourceId: string,
    unitId: string
  ): Promise<number> {
    if (!subcategoryId || !sourceId || !unitId) {
      throw new Error('fetchEmissionValues: subcategoryId, sourceId, and unitId are required.');
    }

    const key = this.cacheKey(subcategoryId, sourceId, unitId);
    const entry = this.totalsCache[key];
    if (isFresh(entry)) {
      return entry.data as number;
    }

    const query =
      `?emissions_sub_category_id=${encodeURIComponent(subcategoryId)}` +
      `&emission_source_id=${encodeURIComponent(sourceId)}` +
      `&measurement_unit_id=${encodeURIComponent(unitId)}`;

    const rows = await this.safeGet<EmissionApiRow[]>(query);

    const rawTotal = rows.reduce((acc, r) => {
      const a13 = toNumberSafe(r.a1_3);
      const a4 = toNumberSafe(r.a4);
      const a5 = toNumberSafe(r.a5);
      return acc + (a13 + a4 + a5);
    }, 0);
    const total = round2(rawTotal);

    this.totalsCache[key] = nowEntry(total);
    return total;
  }

  clearCacheAll() {
    this.totalsCache = {};
  }

  clearCacheFor(subcategoryId: string, sourceId: string, unitId: string) {
    const key = this.cacheKey(subcategoryId, sourceId, unitId);
    delete this.totalsCache[key];
  }
}

export default new ReportDataService();