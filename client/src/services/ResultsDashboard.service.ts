import BaseService from './base.service';

export class ResultsDashboardService extends BaseService {
    constructor() {
        super('/api');
    }
    async materialHotspotsSummary(
        projectId: string,
        stageInstanceId: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            let url = `/dashboard/hotspots/summary?project_id=${projectId}&stage_instance_id=${stageInstanceId}`;

            if (
                (submissionLabel === "Business case" ||
                    submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async renewableEnergySummary(
        projectId: string,
        stageInstanceId: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            let url = `/dashboard/energy/summary?project_id=${projectId}&stage_instance_id=${stageInstanceId}`;

            if (
                (submissionLabel === "Business case" ||
                    submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async emissionsBrkdownSummary(
        projectId: string,
        stageInstanceId: string,
        accountingMethod: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            const elecMethod = accountingMethod === "market" ? "market" : "location";
            let url = `/dashboard/emissions-breakdown/summary?project_id=${projectId}&stage_instance_id=${stageInstanceId}&elec_method=${elecMethod}`;

            if (
                (submissionLabel === "Business case" ||
                    submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async comparisonByStageSummary(
        projectId: string,
        accountingMethod: string,
    ): Promise<any> {
        try {
            let url = `/dashboard/comparison/by-submission?project_id=${projectId}&elec_method=${accountingMethod}`;
            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async comparisonByPeriodSummary(
        projectId: string,
        accountingMethod: string,
    ): Promise<any> {
        try {
            let url = `/dashboard/comparison/by-construction-period?project_id=${projectId}&elec_method=${accountingMethod}`;
            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async offsettingSummary(

        projectId: string,
        stageInstanceId: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            let url = `/dashboard/offsetting/summary?project_id=${projectId}&stage_instance_id=${stageInstanceId}`;

            if (
                (submissionLabel === "Business case" ||
                    submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async optionsComparisonSummary(
        projectId: string,
        accountingMethod: string,
    ): Promise<any> {
        try {
            let url = `/dashboard/options-comparison/summary?project_id=${projectId}&elec_method=${accountingMethod}`;
            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async materialsSummary(
        projectId: string,
        stageInstanceId: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            let url = `/dashboard/materials/summary?project_id=${projectId}&stage_instance_id=${stageInstanceId}`;

            if (
                (submissionLabel === "Business case" ||
                    submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async wasteSummary(
        projectId: string,
        stageInstanceId: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            let url = `/dashboard/waste/summary?project_id=${projectId}&stage_instance_id=${stageInstanceId}`;

            if (
                (submissionLabel === "Business case" ||
                    submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async mitigationSummary(
        projectId: string,
        stageInstanceId: string,
        accountingMethod: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            let url = `/dashboard/mitigation-summary/summary?project_id=${projectId}&stage_instance_id=${stageInstanceId}&elec_method=${accountingMethod}`;

            if (
                (submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async itmmReportingSummary(
        projectId: string,
        stageInstanceId: string,
        accountingMethod: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            let url = `/dashboard/itmm-reporting/lca-module-breakdown?project_id=${projectId}&stage_instance_id=${stageInstanceId}&elec_method=${accountingMethod}`;

            if (
                (submissionLabel === "Business case" ||
                    submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async ratingScoresSummary(
        projectId: string,
        stageInstanceId: string,
        accountingMethod: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        try {
            let url = `/dashboard/ratings/scores?project_id=${projectId}&stage_instance_id=${stageInstanceId}&elec_method=${accountingMethod}`;

            if (
                (submissionLabel === "Business case" ||
                    submissionLabel === "Design") &&
                projectOptionId
            ) {
                url += `&project_option_id=${projectOptionId}`;
            }

            if (submissionLabel === "Construction" && submissionPeriodId) {
                url += `&submission_period_id=${submissionPeriodId}`;
            }

            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    private buildDetailUrl(
        path: string,
        projectId: string,
        stageInstanceId: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): string {
        let url = `${path}?project_id=${projectId}&stage_instance_id=${stageInstanceId}`;
        if (
            (submissionLabel === "Business case" || submissionLabel === "Design") &&
            projectOptionId
        ) {
            url += `&project_option_id=${projectOptionId}`;
        }
        if (submissionLabel === "Construction" && submissionPeriodId) {
            url += `&submission_period_id=${submissionPeriodId}`;
        }
        return url;
    }

    async energyDetail(
        projectId: string, stageInstanceId: string, submissionLabel: string,
        projectOptionId?: string, submissionPeriodId?: string
    ): Promise<any> {
        const url = this.buildDetailUrl('/dashboard/energy/detail', projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId);
        const response = await this.get(url);
        return response.data;
    }

    async materialsDetail(
        projectId: string, stageInstanceId: string, submissionLabel: string,
        projectOptionId?: string, submissionPeriodId?: string
    ): Promise<any> {
        const url = this.buildDetailUrl('/dashboard/materials/detail', projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId);
        const response = await this.get(url);
        return response.data;
    }

    async userEmissions(
        projectId: string, stageInstanceId: string
    ): Promise<any> {
        const url = this.buildDetailUrl('/dashboard/user-emissions', projectId, stageInstanceId, "");
        const response = await this.get(url);
        return response.data;
    }

    async wasteDetail(
        projectId: string, stageInstanceId: string, submissionLabel: string,
        projectOptionId?: string, submissionPeriodId?: string
    ): Promise<any> {
        const url = this.buildDetailUrl('/dashboard/waste/detail', projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId);
        const response = await this.get(url);
        return response.data;
    }

    async carbonValuationDetails(
        projectId: string, stageInstanceId: string, submissionLabel: string,
        projectOptionId?: string, submissionPeriodId?: string
    ): Promise<any> {
        const url = this.buildDetailUrl('/dashboard/carbon-valuation/details', projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId);
        const response = await this.get(url);
        return response.data;
    }

    async carbonStorageDetail(
        projectId: string, stageInstanceId: string, submissionLabel: string,
        projectOptionId?: string, submissionPeriodId?: string
    ): Promise<any> {
        const url = this.buildDetailUrl('/dashboard/carbon-storage/detail', projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId);
        const response = await this.get(url);
        return response.data;
    }

    private buildOrgDetailUrl(
        path: string,
        orgId: string,
        projectCategory?: string,
        submissionLabel?: string,
        programName?: string,
        projectTypecast?: string,
        accountingMethod?: string,
    ): string {
        let url = `${path}?org_id=${orgId}`;
        if (accountingMethod) {
            url += `&elec_method=${accountingMethod}`;
        }

        if (projectCategory) {
            url += `&project_class=${projectCategory}`;
        }

        if (programName) {
            url += `&program_name=${programName}`;
        }

        if (projectTypecast) {
            url += `&project_typecast=${projectTypecast}`;
        }
        if (submissionLabel) {
            url += `&stage=${submissionLabel}`;
        }
        return url;
    }

    async orgEnergyDetail(orgId: string,
        accountingMethod: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submissionLabel: string,): Promise<any> {
        const url = this.buildOrgDetailUrl('/org-dashboard/energy/detail', orgId, projectCategory, submissionLabel, programName, projectTypecast, accountingMethod);
        const response = await this.get(url);
        return response.data;
    }

    async orgMaterialsDetail(orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submissionLabel: string,
        accountingMethod: string,): Promise<any> {
        const url = this.buildOrgDetailUrl('/org-dashboard/materials/detail', orgId, projectCategory, submissionLabel, programName, projectTypecast, accountingMethod);
        const response = await this.get(url);
        return response.data;
    }

    async orgUserEmissions(orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submissionLabel: string,
        accountingMethod: string,): Promise<any> {
        const url = this.buildOrgDetailUrl('/org-dashboard/user-emissions/detail', orgId, projectCategory, submissionLabel, programName, projectTypecast, accountingMethod);
        const response = await this.get(url);
        return response.data;
    }

    async orgWasteDetail(orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submissionLabel: string,
        accountingMethod: string,): Promise<any> {
        const url = this.buildOrgDetailUrl('/org-dashboard/waste/detail', orgId, projectCategory, submissionLabel, programName, projectTypecast, accountingMethod);
        const response = await this.get(url);
        return response.data;
    }

    async orgCarbonValuationDetails(orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submissionLabel: string,
        accountingMethod: string,): Promise<any> {
        const url = this.buildOrgDetailUrl('/org-dashboard/carbon-valuation/detail', orgId, projectCategory, submissionLabel, programName, projectTypecast, accountingMethod);
        const response = await this.get(url);
        return response.data;
    }

    async orgCarbonStorageDetail(orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submissionLabel: string,
        accountingMethod: string,): Promise<any> {
        const url = this.buildOrgDetailUrl('/org-dashboard/carbon-storage/detail', orgId, projectCategory, submissionLabel, programName, projectTypecast, accountingMethod);
        const response = await this.get(url);
        return response.data;
    }


    async orgEmissionsBreakdownSummary(
        orgId: string,
        accountingMethod: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submission: string,
    ): Promise<any> {
        try {

            let url = `/org-dashboard/emissions-breakdown/summary?org_id=${orgId}`;

            if (accountingMethod) {
                url += `&elec_method=${accountingMethod}`;
            }

            if (projectCategory) {
                url += `&project_class=${projectCategory}`;
            }

            if (programName) {
                url += `&program_name=${programName}`;
            }

            if (projectTypecast) {
                url += `&project_typecast=${projectTypecast}`;
            }
            if (submission) {
                url += `&stage=${submission}`;
            }
            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async orgMaterialHotspotsSummary(
        orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submission: string,
    ): Promise<any> {
        try {

            let url = `/org-dashboard/hotspots/summary?org_id=${orgId}`;

            if (projectCategory) {
                url += `&project_class=${projectCategory}`;
            }

            if (programName) {
                url += `&program_name=${programName}`;
            }

            if (projectTypecast) {
                url += `&project_typecast=${projectTypecast}`;
            }
            if (submission) {
                url += `&stage=${submission}`;
            }
            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async orgRenewableEnergySummary(
        orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submission: string,
    ): Promise<any> {
        try {

            let url = `/org-dashboard/energy/summary?org_id=${orgId}`;

            if (projectCategory) {
                url += `&project_class=${projectCategory}`;
            }

            if (programName) {
                url += `&program_name=${programName}`;
            }

            if (projectTypecast) {
                url += `&project_typecast=${projectTypecast}`;
            }
            if (submission) {
                url += `&stage=${submission}`;
            }
            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async orgWasteSummary(
        orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submission: string,
    ): Promise<any> {
        try {

            let url = `/org-dashboard/waste/summary?org_id=${orgId}`;

            if (projectCategory) {
                url += `&project_class=${projectCategory}`;
            }

            if (programName) {
                url += `&program_name=${programName}`;
            }

            if (projectTypecast) {
                url += `&project_typecast=${projectTypecast}`;
            }
            if (submission) {
                url += `&stage=${submission}`;
            }
            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }


    async orgMaterialsSummary(
        orgId: string,
        projectCategory: string,
        programName: string,
        projectTypecast: string,
        submission: string,
    ): Promise<any> {
        try {

            let url = `/org-dashboard/materials/summary?org_id=${orgId}`;

            if (projectCategory) {
                url += `&project_class=${projectCategory}`;
            }

            if (programName) {
                url += `&program_name=${programName}`;
            }

            if (projectTypecast) {
                url += `&project_typecast=${projectTypecast}`;
            }
            if (submission) {
                url += `&stage=${submission}`;
            }
            const response = await this.get(url);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async scopeBreakdown(
        projectId: string,
        stageInstanceId: string,
        accountingMethod: string,
        submissionLabel: string,
        projectOptionId?: string,
        submissionPeriodId?: string
    ): Promise<any> {
        let url = this.buildDetailUrl('/dashboard/scope-breakdown', projectId, stageInstanceId, submissionLabel, projectOptionId, submissionPeriodId);
        url += `&elec_method=${accountingMethod}`;
        const response = await this.get(url);
        return response.data;
    }

    async orgScopeBreakdown(
        orgId: string,
        projectCategory: string,
        accountingMethod: string,
        submissionLabel: string,
        programName?: string,
        projectTypecast?: string
    ): Promise<any> {

        let url = `/org-dashboard/scope-breakdown?org_id=${orgId}`;

        if (accountingMethod) url += `&elec_method=${accountingMethod}`;
        if (projectCategory) url += `&project_class=${projectCategory}`;
        if (programName) url += `&program_name=${programName}`;
        if (projectTypecast) url += `&project_typecast=${projectTypecast}`;
        if (submissionLabel) url += `&stage=${submissionLabel}`;
        const response = await this.get(url);
        return response.data;
    }
}


export default new ResultsDashboardService();
