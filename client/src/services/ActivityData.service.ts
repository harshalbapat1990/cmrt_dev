import BaseService from './base.service';

export interface ActivityDataCreate {
    project_id: string;
    project_stage_instance_id: string;
    dataset_revision_id?: string | null;
    metric_id?: string | null;
    quantity: number;
    unit_id?: string | null;
    ui_table_key: string;
    project_option_id?: string | null;
    component_id?: string | null;
    lifecycle_module_code?: string | null;
    metadata?: Record<string, any> | null;
    created_by?: string | null;
    extra_fields?: Record<string, any> | null;
    emissions_tco2e?: number | string | null;
    submission_period_id?: string | null;
    project_mitigation_id?: string | null;
}

export interface ActivityDataUpdate {
    quantity?: number;
    unit_id?: string;
    metric_id?: string;
    dataset_revision_id?: string | null;
    project_option_id?: string | null;
    lifecycle_module_code?: string | null;
    metadata?: Record<string, any> | null;
    extra_fields?: Record<string, any> | null;
    emissions_tco2e?: number | string | null;
}

export interface ActivityDataOut extends ActivityDataCreate {
    id: string;
    created_at?: string;
    updated_at?: string;
    emissions_tco2e?: string | null;
}

class ActivityDataService extends BaseService {
    private rowRevisionCache = new Map<string, string | null>();
    private projectRevisionCache = new Map<string, string | null>();

    constructor() {
        super('/api');
    }

    clearProjectDatasetRevisionCache(projectId?: string): void {
        if (projectId) {
            this.projectRevisionCache.delete(projectId);
        } else {
            this.projectRevisionCache.clear();
        }
    }

    private async resolveProjectDatasetRevisionId(projectId: string): Promise<string | null> {
        if (this.projectRevisionCache.has(projectId)) {
            return this.projectRevisionCache.get(projectId) ?? null;
        }
        const response = await this.get(`/project-dataset-revisions/by-project/${projectId}`);
        const bindings = Array.isArray(response.data) ? response.data : [];
        const revisionId = bindings[0]?.dataset_revision_id ?? null;
        this.projectRevisionCache.set(projectId, revisionId);
        return revisionId;
    }

    private async resolveRowDatasetRevisionId(rowId: string): Promise<string | null> {
        if (this.rowRevisionCache.has(rowId)) {
            return this.rowRevisionCache.get(rowId) ?? null;
        }
        const row = await this.getRow(rowId);
        const revisionId = row?.dataset_revision_id ?? null;
        this.rowRevisionCache.set(rowId, revisionId);
        return revisionId;
    }

    async createRow(payload: ActivityDataCreate): Promise<ActivityDataOut> {
        const datasetRevisionId =
            payload.dataset_revision_id ??
            payload.extra_fields?.dataset_revision_id ??
            await this.resolveProjectDatasetRevisionId(payload.project_id);

        const payloadWithRevision: ActivityDataCreate = {
            ...payload,
            dataset_revision_id: datasetRevisionId ?? null,
        };

        const response = await this.post('/activity-data', payloadWithRevision);
        const out = response.data as ActivityDataOut;
        this.rowRevisionCache.set(out.id, out.dataset_revision_id ?? payloadWithRevision.dataset_revision_id ?? null);
        this.projectRevisionCache.set(payload.project_id, payloadWithRevision.dataset_revision_id ?? null);
        return out;
    }

    async fetchRows(
        stageInstanceId: string,
        tableKey: string,
        projectOptionId?: string | null,
        submissionPeriodId?: string | null,
        projectMitigationId?: string | null,
    ): Promise<ActivityDataOut[]> {
        const params = new URLSearchParams({
            stage_instance_id: stageInstanceId,
            ui_table_key: tableKey,
        });
        if (projectOptionId) {
            params.set('project_option_id', projectOptionId);
        }
        if (submissionPeriodId) {
            params.set('submission_period_id', submissionPeriodId);
        }
        if (projectMitigationId) {
            params.set('project_mitigation_id', projectMitigationId);
        }
        const response = await this.get(`/activity-data?${params.toString()}`);
        const data = response.data;
        const rows = Array.isArray(data) ? (data as ActivityDataOut[]) : [];
        rows.forEach((r) => this.rowRevisionCache.set(r.id, r.dataset_revision_id ?? null));
        if (rows.length > 0) {
            this.projectRevisionCache.set(rows[0].project_id, rows[0].dataset_revision_id ?? null);
        }
        return rows;
    }

    async getRow(rowId: string): Promise<ActivityDataOut> {
        const response = await this.get(`/activity-data/${rowId}`);
        const row = response.data as ActivityDataOut;
        this.rowRevisionCache.set(row.id, row.dataset_revision_id ?? null);
        this.projectRevisionCache.set(row.project_id, row.dataset_revision_id ?? null);
        return row;
    }

    async updateRow(rowId: string, patch: ActivityDataUpdate): Promise<ActivityDataOut> {
        const http = (await import('@/http')).default;
        const datasetRevisionId =
            patch.dataset_revision_id ??
            patch.extra_fields?.dataset_revision_id ??
            await this.resolveRowDatasetRevisionId(rowId);

        const patchWithRevision: ActivityDataUpdate = {
            ...patch,
            dataset_revision_id: datasetRevisionId ?? null,
        };

        const response = await http.patch(`/api/activity-data/${rowId}`, patchWithRevision);
        const out = response.data as ActivityDataOut;
        this.rowRevisionCache.set(out.id, out.dataset_revision_id ?? patchWithRevision.dataset_revision_id ?? null);
        this.projectRevisionCache.set(out.project_id, out.dataset_revision_id ?? patchWithRevision.dataset_revision_id ?? null);
        return out;
    }

    async deleteRow(rowId: string): Promise<void> {
        await this.delete(`/activity-data/${rowId}`);
    }

    async bulkUpsert(
        stageInstanceId: string,
        tableKey: string,
        rows: ActivityDataCreate[],
        projectMitigationId?: string | null,
        projectOptionId?: string | null,
        submissionPeriodId?: string | null,
    ): Promise<ActivityDataOut[]> {
        const params = new URLSearchParams({
            stage_instance_id: stageInstanceId,
            ui_table_key: tableKey,
        });
        if (projectMitigationId) {
            params.set('project_mitigation_id', projectMitigationId);
        }
        if (projectOptionId) {
            params.set('project_option_id', projectOptionId);
        }
        if (submissionPeriodId) {
            params.set('submission_period_id', submissionPeriodId);
        }
        const rowsWithRevision: ActivityDataCreate[] = await Promise.all(
            rows.map(async (r) => {
                const revisionId =
                    r.dataset_revision_id ??
                    r.extra_fields?.dataset_revision_id ??
                    await this.resolveProjectDatasetRevisionId(r.project_id);
                return {
                    ...r,
                    dataset_revision_id: revisionId ?? null,
                };
            })
        );

        const response = await this.post(`/activity-data/bulk?${params.toString()}`, rowsWithRevision);
        const data = response.data;
        const out = Array.isArray(data) ? (data as ActivityDataOut[]) : [];
        out.forEach((r) => this.rowRevisionCache.set(r.id, r.dataset_revision_id ?? null));
        if (out.length > 0) {
            this.projectRevisionCache.set(out[0].project_id, out[0].dataset_revision_id ?? null);
        }
        return out;
    }

    async seedFromDesign(
        designOptionId: string,
        constructionStageInstanceId: string,
        periodIds: string[],
    ): Promise<{ seeded: number }> {
        const response = await this.post('/activity-data/seed-from-design', {
            design_option_id: designOptionId,
            construction_stage_instance_id: constructionStageInstanceId,
            period_ids: periodIds,
        });
        return response.data;
    }
}

export default new ActivityDataService();