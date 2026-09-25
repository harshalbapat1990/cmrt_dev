import BaseService from './base.service';
export interface UnitOption {
    id: string;
    name: string;
    label: string | null;
    is_canonical: boolean;
    to_canonical_factor: number | null;
    canonical_unit_id: string | null;
    canonical_unit_code: string | null;  // code of the canonical unit (e.g. "m2")
}

const CACHE_EXPIRATION = 10 * 60 * 1000; // 10 minutes

const categoriesCache = {
    data: null as any[] | null,
    timestamp: 0,
    cacheDurationMs: CACHE_EXPIRATION
};

const unitsCache = {
    data: null as any[] | null,
    timestamp: 0,
    cacheDurationMs: CACHE_EXPIRATION
};

const electricityUnitsCache = {
    data: null as UnitOption[] | null,
    timestamp: 0,
    cacheDurationMs: CACHE_EXPIRATION
};

const masterTypeCache = {
    data: null as any[] | null,
    timestamp: 0,
    cacheDurationMs: CACHE_EXPIRATION
};

// const typecastCache = {
//     data: null as any[] | null,
//     timestamp: 0,
//     cacheDurationMs: CACHE_EXPIRATION
// };

export class LookupsService extends BaseService {
    constructor() {
        super('/api');
    }

    private datasetRevisionCache = new Map<string, string | null>();

    clearProjectDatasetRevisionCache(projectId?: string): void {
        if (projectId) {
            this.datasetRevisionCache.delete(projectId);
        } else {
            this.datasetRevisionCache.clear();
        }
    }

    async resolveProjectDatasetRevisionId(projectId: string): Promise<string | null> {
        if (this.datasetRevisionCache.has(projectId)) {
            return this.datasetRevisionCache.get(projectId) ?? null;
        }
        try {
            const resp = await this.get(`/project-dataset-revisions/by-project/${projectId}`);
            const bindings = Array.isArray(resp.data) ? resp.data : [];
            const revisionId = bindings[0]?.dataset_revision_id ?? null;
            this.datasetRevisionCache.set(projectId, revisionId);
            return revisionId;
        } catch {
            this.datasetRevisionCache.set(projectId, null);
            return null;
        }
    }

    /**
     * Get all category data
     * @param topLevelOnly - Filter to only top-level categories
     * @returns {Promise<Array>} - Array of category data
     */
    async fetchCategories(topLevelOnly: boolean = false) {
        const now = Date.now();
        // Check if we have valid cached data
        if (categoriesCache.data && (now - categoriesCache.timestamp < CACHE_EXPIRATION)) {
            return categoriesCache.data;
        }
        try {
            // axios response has .data property and status is on response object
            const params = topLevelOnly ? '?top_level_only=true&skip=0&limit=100' : '';
            const response = await this.get(`/emissions-categories${params}`);
            const rawData = response.data;
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            // Update the cache
            categoriesCache.data = rawData;
            categoriesCache.timestamp = now;

            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching categories:', error.message);
            throw error;
        }
    }

    /**
     * Get child categories by parent category ID
     * @param parentCategoryId - Parent category UUID
     * @returns {Promise<Array>} - Array of child category data
     */
    async fetchCategoriesByParent(parentCategoryId: any) {
        try {
            const response = await this.get(`/emissions-categories?parent_category_id=${encodeURIComponent(parentCategoryId)}&skip=0&limit=100`);
            const rawData = response.data;
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching categories by parent:', error.message);
            throw error;
        }
    }

    /**
     * Get all sub category data
     * Now delegates to the new emissions_categories hierarchy.
     * @returns {Promise<Array>} - Array of category data
     */
    async fetchSubCategories() {
        return this.fetchCategories(false);
    }

    /**
    * Get all sub category data by category id
    * @returns {Promise<Array>} - Array of sub category data
    */
    async fetchSubcategoriesByCategory(
        categoryId: any,
        projectId?: string
    ) {
        try {
            const params = new URLSearchParams({
                parent_category_id: categoryId,
                skip: "0",
                limit: "100",
            });

            if (projectId) {
                params.set("project_id", projectId);
            }

            const response = await this.get(
                `/emissions-categories?${params}`
            );

            const rawData = response.data;

            if (!Array.isArray(rawData)) {
                throw new Error(
                    `Expected array but received ${typeof rawData}`
                );
            }

            return rawData;

        } catch (error: any) {
            console.error(
                "LookupData: Error fetching subcategories by category:",
                error.message
            );
            throw error;
        }
    }


    /**
     * Get emission sources, optionally filtered by sub-category ID.
     * Note: sub-category filtering only works when emission_source.emissions_sub_category_id
     * values align with the IDs being passed. Pass null/undefined to return all sources.
     * @param subcategoryId - Optional sub-category UUID filter
     * @returns {Promise<Array>} - Array of emission source data
     */
    async fetchSources(subcategoryId?: any) {
        try {
            const url = subcategoryId
                ? `/lookup/emission-sources?emissions_sub_category_id=${encodeURIComponent(subcategoryId)}&skip=0&limit=200`
                : `/lookup/emission-sources?skip=0&limit=200`;
            const response = await this.get(url);
            const rawData = response.data;
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            return rawData;
        } catch (error: any) {
            console.error('LookupData: Error fetching sources:', error.message);
            throw error;
        }
    }

    async fetchGrade3Subcategories(categoryName: string): Promise<{ value: string, label: string }[]> {
        try {
            const response = await this.get(
                `/background-grade-metrics?grade_id=3&emissions_category=${encodeURIComponent(categoryName)}&limit=500`
            );
            const rawData = response.data;
            if (!Array.isArray(rawData)) return [];
            const seen = new Set<string>();
            const result: { value: string, label: string }[] = [];
            for (const item of rawData) {
                const name: string = item.emissions_subcategory ?? "";
                if (name && !seen.has(name)) {
                    seen.add(name);
                    result.push({ value: name, label: name });
                }
            }
            return result;
        } catch (error: any) {
            console.error('LookupData: Error fetching grade 3 subcategories:', error.message);
            throw error;
        }
    }

    async fetchGrade3Sources(categoryName: string, subcategoryName: string): Promise<{ value: string, label: string }[]> {
        try {
            const response = await this.get(
                `/background-grade-metrics?grade_id=3&emissions_category=${encodeURIComponent(categoryName)}&emissions_subcategory=${encodeURIComponent(subcategoryName)}&limit=500`
            );
            const rawData = response.data;
            if (!Array.isArray(rawData)) return [];
            const seen = new Set<string>();
            const result: { value: string, label: string }[] = [];
            for (const item of rawData) {
                const name: string = item.emissions_source ?? "";
                if (name && !seen.has(name)) {
                    seen.add(name);
                    result.push({ value: name, label: name });
                }
            }
            return result;
        } catch (error: any) {
            console.error('LookupData: Error fetching grade 3 sources:', error.message);
            throw error;
        }
    }

    /**
     * Get all units data
     * @returns {Promise<Array>} - Array of units data
     */
    async fetchUnits() {
        const now = Date.now();
        // Check if we have valid cached data
        if (unitsCache.data && (now - unitsCache.timestamp < CACHE_EXPIRATION)) {
            return unitsCache.data;
        }
        try {
            // axios response has .data property and status is on response object
            const response = await this.get(`/lookup/units`);
            const rawData = response.data;
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            // Update the cache
            unitsCache.data = rawData;
            unitsCache.timestamp = now;

            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching units:', error.message);
            throw error;
        }
    }

    /**
     * Get units valid for a specific emission source.
     * Falls back to all units if the source-specific endpoint returns nothing.
     * @param sourceId - emission source UUID
     * @returns {Promise<Array>} - Array of {id, name} unit objects
     */
    async fetchUnitsBySource(sourceId: string): Promise<UnitOption[]> {
        try {
            const response = await this.get(`/lookup/emission-sources/${encodeURIComponent(sourceId)}/units`);
            const rawData = response.data;
            if (Array.isArray(rawData) && rawData.length > 0) {
                return rawData;
            }
            // Fallback to all units if none found for the source
            return await this.fetchUnits();
        } catch {
            return await this.fetchUnits();
        }
    }

    async fetchUnitsByTypecast(typecastId: string, gradeIds?: number[]): Promise<UnitOption[]> {
        try {
            const gradeParam = gradeIds && gradeIds.length > 0 ? `&grade_ids=${gradeIds.join(",")}` : "";
            const response = await this.get(`/lookup/benchmark-typecasts/${encodeURIComponent(typecastId)}/units?${gradeParam}`);
            const rawData = response.data;
            if (Array.isArray(rawData) && rawData.length > 0) {
                return rawData;
            }
            return await this.fetchUnits();
        } catch {
            return await this.fetchUnits();
        }
    }

    // ---------------------------------------------------------------
    // BGM-grade-filtered lookups (used by G2 / G3+4 data-entry tables)
    // ---------------------------------------------------------------
    async fetchBgmCategories(gradeIds: number[], projectId?: string, useOrgJurisdiction?: boolean): Promise<any[]> {
        try {
            const params = new URLSearchParams({
                grade_ids: gradeIds.join(","),
            });
            if (projectId) params.set("project_id", projectId);
            if (useOrgJurisdiction) params.set("use_org_jurisdiction", "true");
            const response = await this.get(`/lookup/bgm-categories?${params}`);
            return Array.isArray(response.data) ? response.data : [];
        } catch {
            return [];
        }
    }

    async fetchBgmSubcategories(gradeIds: number[], categoryId: string, projectId?: string, useOrgJurisdiction?: boolean): Promise<any[]> {
        try {
            const params = new URLSearchParams({
                grade_ids: gradeIds.join(","),
                category_id: categoryId,
            });
            if (projectId) params.set("project_id", projectId);
            if (useOrgJurisdiction) params.set("use_org_jurisdiction", "true");
            const response = await this.get(`/lookup/bgm-subcategories?${params}`);
            return Array.isArray(response.data) ? response.data : [];
        } catch {
            return [];
        }
    }

    async fetchBgmSources(gradeIds: number[], subcategoryId: string, projectId?: string, useOrgJurisdiction?: boolean): Promise<any[]> {
        try {
            const params = new URLSearchParams({
                grade_ids: gradeIds.join(","),
                subcategory_id: subcategoryId,
            });
            if (projectId) params.set("project_id", projectId);
            if (useOrgJurisdiction) params.set("use_org_jurisdiction", "true");
            const response = await this.get(`/lookup/bgm-sources?${params}`);
            return Array.isArray(response.data) ? response.data : [];
        } catch {
            return [];
        }
    }

    async fetchBgmSourceUnits(gradeIds: number[], subcategoryId: string, source: string, datasetRevisionId?: string | null): Promise<UnitOption[]> {
        try {
            const params = new URLSearchParams({
                grade_ids: gradeIds.join(","),
                subcategory_id: subcategoryId,
                source,
            });
            if (datasetRevisionId) params.set("dataset_revision_id", datasetRevisionId);
            const response = await this.get(`/lookup/bgm-source-units?${params.toString()}`);
            const data = Array.isArray(response.data) ? response.data : [];
            if (data.length > 0) return data;
            return await this.fetchUnits();
        } catch {
            return await this.fetchUnits();
        }
    }

    /**
     * Get unit options for electricity tables: MWh (canonical) plus every unit
     * that converts to MWh via the unit_conversions table (e.g. kWh, GWh).
     * Falls back to a hardcoded MWh-only option if the endpoint is unavailable.
     */
    async fetchElectricityUnits(): Promise<UnitOption[]> {
        const now = Date.now();
        if (electricityUnitsCache.data && (now - electricityUnitsCache.timestamp < CACHE_EXPIRATION)) {
            return electricityUnitsCache.data;
        }
        try {
            const response = await this.get(`/lookup/electricity-units`);
            const data: UnitOption[] = Array.isArray(response.data) ? response.data : [];
            if (data.length > 0) {
                electricityUnitsCache.data = data;
                electricityUnitsCache.timestamp = now;
                return data;
            }
        } catch {
            // fall through to default
        }
        // Fallback: return MWh-only so the table stays functional
        return [{ id: "", name: "MWh", label: "MWh", is_canonical: true, to_canonical_factor: 1, canonical_unit_id: null, canonical_unit_code: "MWh" }];
    }

    /**
    * Get all mastertype data
    * @returns {Promise<Array>} - Array of mastertype data
    */
    async fetchMasterTypes() {
        const now = Date.now();
        // Check if we have valid cached data
        if (masterTypeCache.data && (now - masterTypeCache.timestamp < CACHE_EXPIRATION)) {
            return masterTypeCache.data;
        }
        try {
            const response = await this.get(`/benchmark-mastertypes`);
            const rawData = response.data;
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            // Update the cache
            masterTypeCache.data = rawData;
            masterTypeCache.timestamp = now;

            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching mastertypes:', error.message);
            throw error;
        }
    }



    /**
    * Get all mastertype data
    * @returns {Promise<Array>} - Array of mastertype data
    */
    async fetchMasterTypesbyProjectId(projectId: string): Promise<any[]> {
        if (!projectId) return [];
        const now = Date.now();
        // Check if we have valid cached data
        if (masterTypeCache.data && (now - masterTypeCache.timestamp < CACHE_EXPIRATION)) {
            return masterTypeCache.data;
        }
        try {
            const response = await this.get(`/benchmark-mastertypes?project_id=${encodeURIComponent(projectId)}`);
            const rawData = response.data;
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }
            // Update the cache
            masterTypeCache.data = rawData;
            masterTypeCache.timestamp = now;

            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching mastertypes:', error.message);
            throw error;
        }
    }


    /**
    * Get all typecast data by mastertype id
    * @param masterTypeId - Mastertype UUID
    * @param projectId - Optional project UUID to filter by jurisdiction
    * @returns {Promise<Array>} - Array of typecasts data
    */
    async fetchTypecasts(masterTypeId: any, projectId?: string) {
        try {
            // axios response has .data property and status is on response object
            let url = `/benchmark-typecasts?mastertype_id=${encodeURIComponent(masterTypeId)}`;
            if (projectId) url += `&project_id=${encodeURIComponent(projectId)}`;
            const response = await this.get(url);
            const rawData = response.data;
            if (!Array.isArray(rawData)) {
                throw new Error(`Expected array but received ${typeof rawData}`);
            }

            return rawData;

        } catch (error: any) {
            console.error('LookupData: Error fetching typecasts:', error.message);
            throw error;
        }
    }

    async fetchAllTypecasts() {
        try {
            const response = await this.get(`/benchmark-typecasts`);
            return response.data;
        }
        catch (error: any) {
            console.error('LookupData: Error fetching all typecasts:', error.message);
            throw error;
        }
    }

}

export default new LookupsService();