import http from '@/http';
import BaseService from './base.service';

export interface ProjectOption {
    id: string;
    project_id: string;
    stage_instance_id: string;
    report_number: number;
    option_number: number;
    label: string;
    is_default: boolean;
    approval_status: string;
    current_justification?: string | null;
    exec_summary?: string | null;
    exec_summary_author?: string | null;
    exec_summary_date?: string | null;
    created_at?: string;
    total_emissions_tco2e?: string | number | null;
}

class ProjectOptionsService extends BaseService {
    constructor() {
        super('/api');
    }

    async fetchOptions(stageInstanceId: string, reportNumber?: number): Promise<ProjectOption[]> {
        const params = new URLSearchParams({ stage_instance_id: stageInstanceId });
        if (reportNumber != null) params.set('report_number', String(reportNumber));
        const response = await this.get(`/project-options?${params.toString()}`);
        const data = response.data;
        return Array.isArray(data) ? data : [];
    }

    async ensureOptions(stageInstanceId: string): Promise<ProjectOption[]> {
        const response = await this.post(`/project-options/ensure?stage_instance_id=${stageInstanceId}`, {});
        const data = response.data;
        return Array.isArray(data) ? data : [];
    }

    async createSubOption(
        projectId: string,
        stageInstanceId: string,
        reportNumber: number,
        label: string,
    ): Promise<ProjectOption> {
        const response = await this.post('/project-options', {
            project_id: projectId,
            stage_instance_id: stageInstanceId,
            report_number: reportNumber,
            label,
        });
        return response.data;
    }

    async renameOption(optionId: string, label: string): Promise<ProjectOption> {
        const response = await http.patch(`/api/project-options/${optionId}/rename`, { label });
        return response.data;
    }

    async setDefaultOption(optionId: string): Promise<ProjectOption> {
        const response = await this.post(`/project-options/${optionId}/set-default`, {});
        return response.data;
    }

    async deleteOption(optionId: string): Promise<void> {
        await this.delete(`/project-options/${optionId}`);
    }

    async copyOption(sourceId: string, targetId: string): Promise<{ copied: number }> {
        const response = await this.post(`/project-options/${sourceId}/copy-to/${targetId}`, {});
        return response.data;
    }

    // -------------------------------------------------------------------------
    // Per-report approval workflow
    // Each method returns the updated options for the entire report.
    // -------------------------------------------------------------------------

    async submitReport(optionId: string): Promise<ProjectOption[]> {
        const response = await this.post(`/project-options/${optionId}/submit`, {});
        return response.data;
    }

    async approveReport(optionId: string, justification?: string): Promise<ProjectOption[]> {
        const body = justification?.trim() ? { justification: justification.trim() } : {};
        const response = await this.post(`/project-options/${optionId}/approve`, body);
        return response.data;
    }

    async rejectReport(optionId: string, justification: string): Promise<ProjectOption[]> {
        const response = await this.post(`/project-options/${optionId}/reject`, { justification: justification.trim() });
        return response.data;
    }

    async requestReopen(optionId: string, justification: string): Promise<ProjectOption[]> {
        const response = await this.post(`/project-options/${optionId}/request-reopen`, { justification: justification.trim() });
        return response.data;
    }

    async approveReopen(optionId: string, justification?: string): Promise<ProjectOption[]> {
        const body = justification?.trim() ? { justification: justification.trim() } : {};
        const response = await this.post(`/project-options/${optionId}/approve-reopen`, body);
        return response.data;
    }

    async rejectReopen(optionId: string, justification: string): Promise<ProjectOption[]> {
        const response = await this.post(`/project-options/${optionId}/reject-reopen`, { justification: justification.trim() });
        return response.data;
    }

    async saveExecSummary(optionId: string, text: string | null, author?: string, date?: string): Promise<ProjectOption> {
        const response = await http.patch(`/api/project-options/${optionId}/exec-summary`, {
            exec_summary: text,
            exec_summary_author: text ? (author ?? null) : null,
            exec_summary_date: text ? (date ?? null) : null,
        });
        return response.data;
    }
}

export default new ProjectOptionsService();
