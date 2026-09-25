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

export type OrganizationType = 'DESIGNERS' | 'CONTRACTORS' | 'PLATFORM_OPERATOR';

export type OrganizationDto = {
  id?: string | number;
  name: string;
  shortName?: string;
  code?: string;
  aliases?: string[];
  type?: OrganizationType;
};

export class OrganizationService extends BaseService {
  constructor() {
    super('/api/organizations');
  }

  private caches: Record<string, CacheEntry<OrganizationDto[]>> = {
    designer: makeEmptyCache<OrganizationDto[]>(),
    construction: makeEmptyCache<OrganizationDto[]>(),
    platformOperator: makeEmptyCache<OrganizationDto[]>(),
    all: makeEmptyCache<OrganizationDto[]>(),
  };

  private async safeGet(path: string): Promise<any> {
    try {
      const response = await this.get(path);
      const data = response?.data;
      if (!Array.isArray(data)) {
        throw new Error(`Expected array but received ${typeof data} at '${path}'`);
      }
      return data;
    } catch (error: any) {
      console.error(`Organization service GET ${path} failed:`, error?.message ?? error);
      throw error;
    }
  }

  async fetchOrganizations(type: OrganizationType): Promise<OrganizationDto[]> {
    const cache = this.caches[type];
    if (isFresh(cache)) return cache.data || [];

    const raw = await this.safeGet(`?organization_type=${type}&limit=500`);
    this.caches[type] = nowEntry(raw);
    return raw;
  }

  async fetchAllOrganizations(): Promise<OrganizationDto[]> {
    const cache = this.caches['all'];
    if (isFresh(cache)) return cache.data || [];

    const raw = await this.safeGet(`?limit=500`);
    this.caches['all'] = nowEntry(raw);
    return raw;
  }

  async fetchOrganizationById(id: string | number): Promise<any> {
    try {
      const response = await this.get(`/${id}`);
      return response?.data;
    } catch (error: any) {
      console.error(`Organization service GET /${id} failed:`, error?.message ?? error);
      throw error;
    }
  }

  async filterOrganizations(type: OrganizationType, query: string): Promise<OrganizationDto[]> {
    const list = await this.fetchOrganizations(type);
    const q = (query || '').trim().toLowerCase();
    if (!q) return list.slice(0, 50);
    return list.filter((o) => {
      const base = o.name?.toLowerCase() || '';
      const aliasHit = (o.aliases || []).some(a => a.toLowerCase().includes(q));
      const shortHit = (o.shortName || '').toLowerCase().includes(q);
      const codeHit = (o.code || '').toLowerCase().includes(q);
      return base.includes(q) || aliasHit || shortHit || codeHit;
    });
  }

  clearCacheAll() {
    this.caches.designer = makeEmptyCache<OrganizationDto[]>();
    this.caches.construction = makeEmptyCache<OrganizationDto[]>();
    this.caches.platformOperator = makeEmptyCache<OrganizationDto[]>();
    this.caches.all = makeEmptyCache<OrganizationDto[]>();
  }

  clearCacheByType(type: OrganizationType) {
    this.caches[type] = makeEmptyCache<OrganizationDto[]>();
  }
}

export default new OrganizationService();