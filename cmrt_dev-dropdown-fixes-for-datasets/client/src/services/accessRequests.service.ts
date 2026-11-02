import BaseService from './base.service';

export type AccessRequestEnriched = {
  id: string;
  request_type: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  requester_user_id: string | null;
  target_user_id: string | null;
  requested_role_id: string | null;
  scope_type: string;
  scope_id: string | null;
  organisation_id: string | null;
  project_id: string | null;
  reason: string | null;
  decision_note: string | null;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  created_on: string | null;
  updated_on: string | null;
  requester_email: string | null;
  requester_display_name: string | null;
  organisation_name: string | null;
  project_name: string | null;
};

class AccessRequestsService extends BaseService {
  constructor() {
    super('/api/access-requests');
  }

  async fetchPending(requestType?: string): Promise<AccessRequestEnriched[]> {
    let path = '?status=PENDING&limit=200';
    if (requestType) path += `&request_type=${encodeURIComponent(requestType)}`;
    const res = await this.get(path);
    return res?.data ?? [];
  }

  async approve(id: string, decisionNote?: string): Promise<void> {
    await this.post(`/${id}/approve`, { decision_note: decisionNote ?? null });
  }

  async reject(id: string, reason: string): Promise<void> {
    await this.post(`/${id}/reject`, { decision_note: reason });
  }

  async fetchMySuperAdminRequest(): Promise<AccessRequestEnriched | null> {
    const res = await this.get('/mine/super-admin');
    return res?.data ?? null;
  }

  async requestSuperAdmin(reason: string): Promise<AccessRequestEnriched> {
    const res = await this.post('', {
      request_type: 'SUPER_ADMIN',
      scope_type: 'GLOBAL',
      scope_id: null,
      reason,
    });
    return res.data;
  }
}

export default new AccessRequestsService();
