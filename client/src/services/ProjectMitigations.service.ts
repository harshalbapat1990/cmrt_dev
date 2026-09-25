import BaseService from './base.service';

export type ProjectMitigationOut = {
    id: string;
    project_id: string;
    project_stage_instance_id: string;
    project_option_id?: string | null;
    submission_stage: string;
    name: string;
    mitigation_type: string;
    lifecycle_phase: string;
    lifecycle_phase_label: string;
    notes?: string | null;
    group_label?: string | null;
    created_at?: string;
    updated_at?: string | null;
};

export type ProjectMitigationCreateBody = {
    project_id: string;
    project_stage_instance_id: string;
    project_option_id?: string | null;
    submission_stage: string;
    name: string;
    mitigation_type: string;
    lifecycle_phase: string;
    lifecycle_phase_label: string;
    notes?: string | null;
    group_label?: string | null;
};

export type ProjectMitigationPatchBody = Partial<{
    name: string;
    mitigation_type: string;
    lifecycle_phase: string;
    lifecycle_phase_label: string;
    notes: string | null;
    group_label: string | null;
}>;

class ProjectMitigationsService extends BaseService {
    constructor() {
        super('/api');
    }

    async list(params: {
        project_stage_instance_id: string;
        project_option_id?: string | null;
        submission_stage?: string;
    }): Promise<ProjectMitigationOut[]> {
        const q = new URLSearchParams({
            project_stage_instance_id: params.project_stage_instance_id,
        });
        if (params.project_option_id) q.set('project_option_id', params.project_option_id);
        if (params.submission_stage) q.set('submission_stage', params.submission_stage);
        const response = await this.get(`/project-mitigations?${q.toString()}`);
        const data = response.data;
        if (Array.isArray(data)) return data;
        if (data && typeof data === "object" && "id" in data) return [data as ProjectMitigationOut];
        return [];
    }

    async create(body: ProjectMitigationCreateBody): Promise<ProjectMitigationOut> {
        const response = await this.post('/project-mitigations', body);
        return response.data as ProjectMitigationOut;
    }

    async patchMitigation(id: string, body: ProjectMitigationPatchBody): Promise<ProjectMitigationOut> {
        const response = await this.patch(`/project-mitigations/${id}`, body);
        return response.data as ProjectMitigationOut;
    }

    async remove(id: string): Promise<void> {
        await this.delete(`/project-mitigations/${id}`);
    }
}

export default new ProjectMitigationsService();