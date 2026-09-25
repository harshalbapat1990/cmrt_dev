import BaseService from './base.service';

export type UserRoleEnriched = {
  user_role_id: string;
  user_id: string;
  user_email: string;
  user_display_name: string | null;
  role_name: string;
  scope_type: string;
  scope_id: string | null;
  org_name: string | null;
  project_name: string | null;
  is_active: boolean;
};

class UserRolesService extends BaseService {
  constructor() {
    super('/api/user-roles');
  }

  async fetchEnriched(params?: {
    role_name?: string;
    scope_type?: string;
    limit?: number;
  }): Promise<UserRoleEnriched[]> {
    const qs = new URLSearchParams();
    if (params?.role_name) qs.set('role_name', params.role_name);
    if (params?.scope_type) qs.set('scope_type', params.scope_type);
    if (params?.limit) qs.set('limit', String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    const res = await this.get(`/enriched${suffix}`);
    return res?.data ?? [];
  }

  async revokeRole(userRoleId: string): Promise<void> {
    await this.patch(`/${userRoleId}`, { is_active: false });
  }

  async transferOrgAdmin(fromUserRoleId: string, toUserId: string): Promise<void> {
    await this.post('/transfer-org-admin', { from_user_role_id: fromUserRoleId, to_user_id: toUserId });
  }

  async assignOrgAdminForSA(orgId: string, userId: string): Promise<void> {
    await this.post('/assign-org-admin', { org_id: orgId, user_id: userId });
  }
}

export default new UserRolesService();
