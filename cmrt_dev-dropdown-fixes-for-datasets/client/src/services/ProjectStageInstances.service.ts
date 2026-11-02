import BaseService from './base.service';


export type ApprovalStatus = 'draft' | 'awaiting_approval' | 'final_approved' | 'rejected' | 'reopen_requested';


export class ProjectStageInstancesService extends BaseService {
    constructor() {
        super('/api/project-stage-instances');
    }

    async fetchStageInstances(instanceId: string): Promise<any[]> {
        // Check if we have valid cached data
        try {
            // axios response has .data property and status is on response object
            const response = await this.get(`/project-stage-instances/${instanceId}`);
            const rawData = response.data;

            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }

            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching user projects:', error.message);
            throw error;
        }
    }

    async submit(instanceId: string): Promise<any> {
        try {
            const response = await this.post(`/${instanceId}/submit`);
            const rawData = response.data;
            return rawData;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async approve(stageInstanceId: any, justification?: string): Promise<any> {
        try {

            const payload = justification?.trim() ? { justification: justification.trim() } : undefined;

            const response = await this.post(`/${stageInstanceId}/approve`, payload);
            const rawData = response.data;

            return rawData;

        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }


    async reject(stageInstanceId: any, justification: string): Promise<any> {
        try {
            const payload = { justification: justification.trim() };

            const response = await this.post(`/${stageInstanceId}/reject`, payload);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }


    async approveReopen(stageInstanceId: string, justification?: string): Promise<any> {
        try {
            const body = {
                justification: justification || null,
            };
            const response = await this.post(`/${stageInstanceId}/approve-reopen`, body);
            const rawData = response.data;

            return rawData;

        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async rejectReopen(stageInstanceId: string, justification: string): Promise<any> {
        try {
            const body = {
                justification: justification.trim(),
            };
            const response = await this.post(`/${stageInstanceId}/reject-reopen`, body);
            const rawData = response.data;

            return rawData;

        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }



    async submitReopen(stageInstanceId: string, justification: string): Promise<any> {
        try {
            const payload = {
                justification: justification.trim(),
                current_justification: justification.trim()
            };
            const response = await this.post(`/${stageInstanceId}/request-reopen`, payload);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

}

export default new ProjectStageInstancesService();