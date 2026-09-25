import BaseService from './base.service';
import type { ConstructionPeriod, ConstructionPeriodStatus } from '../types/reports';

export interface ConstructionPeriodCreate {
  project_id: string;
  stage_instance_id: string;
  frequency: string;
  period_label: string;
  period_start_date: string;
  period_end_date: string;
  due_date?: string | null;
}

class ConstructionPeriodsServiceClass extends BaseService {
  constructor() {
    super('/api/construction-periods');
  }

  async listPeriods(stageInstanceId: string): Promise<ConstructionPeriod[]> {
    const response = await this.get(`?stage_instance_id=${stageInstanceId}`);
    return response.data;
  }

  async createPeriod(payload: ConstructionPeriodCreate): Promise<ConstructionPeriod> {
    const response = await this.post('', payload);
    return response.data;
  }

  async submit(periodId: string, comment?: string): Promise<ConstructionPeriod> {
    const response = await this.post(`/${periodId}/submit`, comment ? { comment } : {});
    return response.data;
  }

  async approve(periodId: string, comment?: string): Promise<ConstructionPeriod> {
    const response = await this.post(`/${periodId}/approve`, comment ? { comment } : {});
    return response.data;
  }

  async reject(periodId: string, rejection_reason: string): Promise<ConstructionPeriod> {
    const response = await this.post(`/${periodId}/reject`, { rejection_reason });
    return response.data;
  }

  async requestReopen(periodId: string, reopen_reason: string): Promise<ConstructionPeriod> {
    const response = await this.post(`/${periodId}/request-reopen`, { reopen_reason });
    return response.data;
  }

  async approveReopen(periodId: string, comment?: string): Promise<ConstructionPeriod> {
    const response = await this.post(`/${periodId}/approve-reopen`, comment ? { comment } : {});
    return response.data;
  }

  async rejectReopen(periodId: string, rejection_reason: string): Promise<ConstructionPeriod> {
    const response = await this.post(`/${periodId}/reject-reopen`, { rejection_reason });
    return response.data;
  }

  async saveExecSummary(periodId: string, text: string | null, author?: string, date?: string): Promise<ConstructionPeriod> {
    const response = await this.patch(`/${periodId}/exec-summary`, {
      exec_summary: text,
      exec_summary_author: text ? (author ?? null) : null,
      exec_summary_date: text ? (date ?? null) : null,
    });
    return response.data;
  }
}

export const ConstructionPeriodsService = new ConstructionPeriodsServiceClass();
export type { ConstructionPeriod, ConstructionPeriodStatus };
