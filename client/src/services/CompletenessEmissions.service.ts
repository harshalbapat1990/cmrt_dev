import BaseService from "./base.service";
import type { CompletenessModuleKey } from "@/pages/smallProject/dataEntry/completenessConstants";

export interface ModuleCompletenessInput {
    module: CompletenessModuleKey;
    completeness_pct: number;
}

export interface CalculateCompletenessRequest {
    project_id: string;
    stage_instance_id: string;
    project_option_id?: string | null;
    submission_period_id?: string | null;
    elec_method?: "location" | "market";
    modules: ModuleCompletenessInput[];
}

export interface ModuleCalculationResult {
    module: CompletenessModuleKey;
    label: string;
    completeness_pct: number | string;
    base_emissions_tco2e: number | string;
    upscaling_adjustment_tco2e: number | string;
}

export interface CalculateCompletenessResponse {
    modules: ModuleCalculationResult[];
    total_uplift_tco2e: number | string;
}

class CompletenessEmissionsService extends BaseService {
    constructor() {
        super("/api/dashboard/completeness-emissions-breakdown");
    }

    async calculate(payload: CalculateCompletenessRequest): Promise<CalculateCompletenessResponse> {
        const response = await this.post("/calculate", payload);
        return response.data as CalculateCompletenessResponse;
    }
}

export default new CompletenessEmissionsService();
