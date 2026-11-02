import BaseService from './base.service';

const CACHE_EXPIRATION = 10 * 60 * 1000;
const emissionDataCache = {
    data: null as any[] | null,
    timestamp: 0,
    cacheDurationMs: CACHE_EXPIRATION
};
export type CreateEmissionEntryRequest = {
    project_id: string;
    project_reporting_submission_id: string;
    emissions_sub_category_id: string;
    emission_source_id: string;
    measurement_unit_id: string;
    emission_factor_id?: string;
    data_quality: string;
    quantity: number;
    emissions_tco2e: number;
    notes?: string;
    submitted_by_user_id: string;
    submitted_on?: string;
};


export class EmissionEntriesService extends BaseService {
    constructor() {
        super('/api/emission_entries');
    }

    async fetchEmissionDetails() {
        const now = Date.now();

        // Check if we have valid cached data
        if (emissionDataCache.data && (now - emissionDataCache.timestamp < CACHE_EXPIRATION)) {
            return emissionDataCache.data;
        }
        try {
            // axios response has .data property and status is on response object
            const response = await this.get(`/get-emission-entries`);
            const rawData = response.data;

            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            // Update the cache
            emissionDataCache.data = rawData;
            emissionDataCache.timestamp = now;

            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching user projects:', error.message);
            throw error;
        }
    }

    async createEmissionEntry(payload: CreateEmissionEntryRequest): Promise<{ id: string }> {
        try {
            // axios response has .data property and status is on response object
            const response = await this.post(`/post-emission-entries`, payload);
            const rawData = response.data;


            if (!Array.isArray(rawData) || rawData.length === 0) {
                throw new Error("Expected a non-empty array response");
            }

            const first = rawData[0];

            if (!first || typeof first.id !== "string") {
                throw new Error("Invalid API response: missing id");
            }

            return { id: first.id };


        } catch (error: any) {
            console.error('LookupData: Error posting user projects:', error.message);
            throw error;
        }
    }
}

export default new EmissionEntriesService();