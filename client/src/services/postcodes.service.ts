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

export class PostcodesService extends BaseService {
  constructor() {
    super('/api/postcodes');
  }

  private postcodesCache: CacheEntry<any> = makeEmptyCache();

  private async safeGet(path: string): Promise<any> {
    try {
      const response = await this.get(path);
      const data = response?.data;

      if (!Array.isArray(data)) {
        throw new Error(`Expected array but received ${typeof data} at '${path}'`);
      }

      return data;
    } catch (error: any) {
      console.error(`Postcode service GET ${path} failed:`, error?.message ?? error);
      throw error;
    }
  }

  async fetchPostcodes(orgId: any): Promise<any> {
    if (isFresh(this.postcodesCache)) {
      return this.postcodesCache.data;
    }
    // const raw = await this.safeGet('/get-all-postcodes');
    const raw = await this.safeGet(`/get-by-jurisdiction/${orgId}`);
    this.postcodesCache = nowEntry(raw);
    return raw;
  }

  clearCacheAll() {
    this.postcodesCache = makeEmptyCache();
  }

  clearPostcodeCache() {
    this.postcodesCache = makeEmptyCache();
  }
}

export default new PostcodesService();