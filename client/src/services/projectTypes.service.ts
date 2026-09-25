import BaseService from './base.service';

const CACHE_EXPIRATION = 10 * 60 * 1000;

type CacheEntry<T> = {
  data: T | null;
  timestamp: number;
  cacheDurationMs: number;
};

function isFresh(entry?: CacheEntry<any>): boolean {
  if (!entry || entry.data === null) return false;
  return Date.now() - entry.timestamp < entry.cacheDurationMs;
}

function nowEntry<T>(data: T, cacheDurationMs = CACHE_EXPIRATION): CacheEntry<T> {
  return { data, timestamp: Date.now(), cacheDurationMs };
}

function makeEmptyCache<T>(): CacheEntry<T> {
  return { data: null, timestamp: 0, cacheDurationMs: CACHE_EXPIRATION };
}

export class ProjectTypesService extends BaseService {
  constructor() {
    super('/api/project-types');
  }

  private projectTypesCache: CacheEntry<any> = makeEmptyCache();
  private projectTypeCastCacheByKey = new Map<string, CacheEntry<any[]>>();

  private async safeGet(path: string): Promise<any> {
    try {
      const response = await this.get(path);
      const data = response?.data;

      if (!Array.isArray(data)) {
        throw new Error(`Expected array but received ${typeof data} at '${path}'`);
      }

      return data;
    } catch (error: any) {
      console.error(`ProjectTypesService GET ${path} failed:`, error?.message ?? error);
      throw error;
    }
  }

  async fetchProjectTypes(): Promise<any> {
    if (isFresh(this.projectTypesCache)) {
      return this.projectTypesCache.data;
    }

    const raw = await this.safeGet('/get-project-types');
    this.projectTypesCache = nowEntry(raw);
    return raw;
  }

  async fetchProjectTypecast(projectTypeId: string | number): Promise<any> {
    
const key = String(projectTypeId).trim();
    if (!key) return [];

    const existing = this.projectTypeCastCacheByKey.get(key);

    if (isFresh(existing)) {
      return (existing!.data as any[]) ?? ['No options'];
    }

    let raw = await this.safeGet(`/typecasts?project_type_id=${projectTypeId}`);
    this.projectTypeCastCacheByKey.set(key, nowEntry(raw));
    return raw;
  }

  clearCacheAll() {
    this.projectTypesCache = makeEmptyCache();
    this.projectTypeCastCacheByKey.clear();
  }

  clearProjectTypesCache() {
    this.projectTypesCache = makeEmptyCache();
  }

  clearProjectTypeCastCache() {
    this.projectTypeCastCacheByKey.clear();
  }
}

export default new ProjectTypesService();