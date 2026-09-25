import BaseService from './base.service';

const CACHE_EXPIRATION = 10 * 60 * 1000; // 10 minutes

const bgGradeMetricCache = {
    data: null as any[] | null,
    timestamp: 0,
    cacheDurationMs: CACHE_EXPIRATION
};



export class BgGradeMetricService extends BaseService {
    constructor() {
        super('/api');
    }

    /**
     * Get all data for a grade
     * @returns {Promise<Array>} - Array of projects data
     */
    async fetchGradeData(gradeId: number) {
        const now = Date.now();
        
        // Check if we have valid cached data
        if (bgGradeMetricCache.data && (now - bgGradeMetricCache.timestamp < CACHE_EXPIRATION)) {
            return bgGradeMetricCache.data;
        }
        try {
            const response = await this.get(`/background-grade-metrics?grade_id=${gradeId}`);
            const rawData = response.data;
            
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            // Update the cache
            bgGradeMetricCache.data = rawData;
            bgGradeMetricCache.timestamp = now;

            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching data entries for a grade:', error.message);
            throw error;
        }
    }

}

export default new BgGradeMetricService();