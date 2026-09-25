import BaseService from './base.service';

const CACHE_EXPIRATION = 10 * 60 * 1000; // 10 minutes

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

export type OrgUser = {
  id: string;
  email: string;
  display_name?: string;
  name?: string;
  date_joined?: string;
  project_roles?: Array<{
    project_id: string;
    project_name: string;
    role_name: string;
    user_role_id: string;
    is_active: boolean;
  }>;
  has_org_admin_role?: boolean;
  org_admin_user_role_id?: string;
};

class OrgAdminService extends BaseService {
  constructor() {
    super('/api/org-admin');
  }

  private orgUsersCache: CacheEntry<OrgUser[]> = makeEmptyCache();
  private projectAdminsCache: Map<string, CacheEntry<any[]>> = new Map();

  async fetchOrgUsers(forceRefresh = false): Promise<OrgUser[]> {
  if (!forceRefresh && isFresh(this.orgUsersCache)) {
    return this.orgUsersCache.data || [];
  }

  const res = await this.get('/users');
  const raw = res?.data ?? [];

  const data: OrgUser[] = raw.map((u: any) => ({
    id: u.user_id,               // ✅ normalize here
    email: u.email,
    display_name: u.display_name,
    name: u.name,
    date_joined: u.date_joined,
    project_roles: u.project_roles || [],
    has_org_admin_role: u.has_org_admin_role ?? false,
    org_admin_user_role_id: u.org_admin_user_role_id ?? undefined,
  }));

  this.orgUsersCache = nowEntry(data);
  return data;
}


  // Add project admin
  async addProjectAdmin(projectId: string, userId: string): Promise<any> {
    try {
      const res = await this.post(`/projects/${projectId}/admins`, {
        user_id: userId,
      });
      
      // Invalidate cache for this project's admins
      this.invalidateProjectAdminsCache(projectId);
      // Also invalidate org users cache as user roles might have changed
      this.orgUsersCache = makeEmptyCache();
      
      return res?.data;
    } catch (error: any) {
      console.error('Failed to add project admin:', error?.message ?? error);
      throw error;
    }
  }

  // Remove project admin
  async removeProjectAdmin(projectId: string, userId: string): Promise<any> {
    try {
      const res = await this.delete(`/projects/${projectId}/admins/${userId}`);
      
      // Invalidate cache for this project's admins
      this.invalidateProjectAdminsCache(projectId);
      // Also invalidate org users cache as user roles might have changed
      this.orgUsersCache = makeEmptyCache();
      
      return res?.data;
    } catch (error: any) {
      console.error('Failed to remove project admin:', error?.message ?? error);
      throw error;
    }
  }

  // Fetch project admins for a specific project with cache
  async fetchProjectAdmins(projectId: string, forceRefresh = false): Promise<any[]> {
    const cacheKey = `project_admins_${projectId}`;
    const cached = this.projectAdminsCache.get(cacheKey);
    
    if (!forceRefresh && cached && isFresh(cached)) {
      return cached.data || [];
    }

    try {
      const res = await this.get(`/projects/${projectId}/admins`);
      const data = res?.data ?? [];
      this.projectAdminsCache.set(cacheKey, nowEntry(data));
      return data;
    } catch (error: any) {
      console.error('Failed to fetch project admins:', error?.message ?? error);
      throw error;
    }
  }

  // Check if a user is a project admin
  async isUserProjectAdmin(projectId: string, userId: string): Promise<boolean> {
    try {
      const admins = await this.fetchProjectAdmins(projectId);
      return admins.some(admin => admin.id === userId || admin.user_id === userId);
    } catch (error) {
      return false;
    }
  }

  // Get all projects where a user is an admin
  async getUserAdminProjects(userId: string): Promise<any[]> {
    try {
      const res = await this.get(`/users/${userId}/admin-projects`);
      return res?.data ?? [];
    } catch (error: any) {
      console.error('Failed to fetch user admin projects:', error?.message ?? error);
      throw error;
    }
  }
      // Delete organization user
    async deleteOrgUser(userId: string): Promise<void> {
      try {
        await this.delete(`/users/${userId}`);

        // Invalidate org users cache
        this.clearOrgUsersCache();
      } catch (error: any) {
        console.error("Failed to delete org user:", error?.message ?? error);
        throw error;
      }
    }


  // Invalidate cache for a specific project's admins
  private invalidateProjectAdminsCache(projectId: string): void {
    const cacheKey = `project_admins_${projectId}`;
    this.projectAdminsCache.delete(cacheKey);
  }

  // Clear all caches
  clearAllCaches(): void {
    this.orgUsersCache = makeEmptyCache();
    this.projectAdminsCache.clear();
  }

  // Clear org users cache only
  clearOrgUsersCache(): void {
    this.orgUsersCache = makeEmptyCache();
  }

  async addOrgAdmin(userId: string): Promise<void> {
    await this.post('/admins', { user_id: userId });
    this.orgUsersCache = makeEmptyCache();
  }

  async removeOrgAdmin(userRoleId: string): Promise<void> {
    await this.delete(`/admins/${userRoleId}`);
    this.orgUsersCache = makeEmptyCache();
  }

  async fetchOrgMembersForSA(orgId: string): Promise<OrgUser[]> {
    const res = await this.get(`/users?org_id=${orgId}`);
    const raw = res?.data ?? [];
    return raw.map((u: any) => ({
      id: u.user_id,
      email: u.email,
      display_name: u.display_name,
      name: u.display_name || u.email,
      date_joined: u.date_joined,
      project_roles: u.project_roles || [],
      has_org_admin_role: u.has_org_admin_role ?? false,
      org_admin_user_role_id: u.org_admin_user_role_id ?? undefined,
    }));
  }
}

export default new OrgAdminService();