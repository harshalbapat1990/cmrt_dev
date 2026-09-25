import BaseService from './base.service';

const CACHE_EXPIRATION = 10 * 60 * 1000; // 10 minutes

const submissionsCache = {
    data: null as any[] | null,
    timestamp: 0,
    cacheDurationMs: CACHE_EXPIRATION
};

export class ProjReportSubmissionsService extends BaseService {
    constructor() {
        super('/api/project-submissions');
    }

    /**
     * Get all stages for a project report
     * @returns {Promise<Array>} - Array of stages data
     */
    async fetchStages(projectId: string) {
        const now = Date.now();
        
        // Check if we have valid cached data
        if (submissionsCache.data && (now - submissionsCache.timestamp < CACHE_EXPIRATION)) {
            return submissionsCache.data;
        }
        try {
            // axios response has .data property and status is on response object
            const response = await this.get(`?project_id=${encodeURIComponent(projectId)}`);
            const rawData = response.data;
            
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            // Update the cache
            submissionsCache.data = rawData;
            submissionsCache.timestamp = now;

            return rawData;

        } catch (error: any) {
            console.error('Stages Data: Error fetching project Stages:', error.message);
            throw error;
        }
    }

    

}

export default new ProjReportSubmissionsService();