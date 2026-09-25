import http from '@/http';
import type { AuditLogRow } from '@/pages/datasets/types';

export interface AuditLogQuery {
  entity_type?: string;
  entity_id?: string;
  action?: string;
  performed_by?: string;
  performed_by_org?: string;
  from_date?: string;
  to_date?: string;
  skip?: number;
  limit?: number;
}

export interface StageResubmissionAuditResult {
  has_prior_rejection: boolean;
  window_from: string | null;
  window_to: string | null;
  stage_name: string;
  rows: AuditLogRow[];
}

export async function fetchAuditLogs(params: AuditLogQuery = {}): Promise<AuditLogRow[]> {
  const res = await http.get<AuditLogRow[]>('/api/audit-logs', { params });
  return res.data;
}

export async function fetchProjectAuditLogs(
  projectId: string,
  params: Pick<AuditLogQuery, 'action' | 'from_date' | 'to_date' | 'skip' | 'limit'> = {},
): Promise<AuditLogRow[]> {
  const res = await http.get<AuditLogRow[]>(`/api/audit-logs/project/${projectId}`, { params });
  return res.data;
}

export async function fetchStageResubmissionAudit(
  stageInstanceId: string,
  projectOptionId?: string,
): Promise<StageResubmissionAuditResult> {
  const params = projectOptionId ? { project_option_id: projectOptionId } : undefined;
  const res = await http.get<StageResubmissionAuditResult>(
    `/api/audit-logs/stage/${stageInstanceId}/resubmission`,
    { params },
  );
  return res.data;
}
