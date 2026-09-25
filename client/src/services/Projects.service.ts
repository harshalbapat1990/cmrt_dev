import BaseService from './base.service';

export class ProjectsService extends BaseService {
    constructor() {
        super('/api');
    }

    async fetchProjectDetails(projectId: string) {
        try {
            const response = await this.get(`/projects/${projectId}`);
            return response.data;
        } catch (error: any) {
            console.error('ProjectsService: Error fetching project details:', error.message);
            throw error;
        }
    }
    async fetchAllProjects() {
        try {
            const response = await this.get('/projects');
            return response.data;
        } catch (error: any) {
            console.error('ProjectsService: Error fetching all project details:', error.message);
            throw error;
        }
    }
}

export default new ProjectsService();