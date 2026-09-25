import BaseService from './base.service';



export class EmissionCalculationsService extends BaseService {
    constructor() {
        super('/api');

    }

    private toNumberOrNull(value: any): number | null {
    if (value === null || value === undefined || value === "") return null;

    const n = Number(value);
    return Number.isFinite(n) ? n : null;
}

private normalizeUserEmissionSummary(response: any): any {
    const data = response?.data ?? response ?? {};

    return {
        absoluteEmissions:
            this.toNumberOrNull(data.interim_total_tco2e) ??
            this.toNumberOrNull(data.absoluteEmissions) ??
            this.toNumberOrNull(data.absolute_emissions) ??
            this.toNumberOrNull(data.total_emissions_tco2e) ??
            this.toNumberOrNull(data.interim_absolute_emissions_tco2e) ??
            0,

        baseCaseAbsoluteEmissions:
            this.toNumberOrNull(data.base_case_emissions_tco2e) ??
            this.toNumberOrNull(data.baseCaseAbsoluteEmissions) ??
            this.toNumberOrNull(data.base_case_absolute_emissions) ??
            null,

        relativeUserEmissions:
            this.toNumberOrNull(data.final_user_emissions_tco2e) ??
            this.toNumberOrNull(data.relativeUserEmissions) ??
            this.toNumberOrNull(data.relative_user_emissions) ??
            null,

        raw: data,
    };
}
        async grade1EmissionValues(payload: any): Promise<any> {
        try {
            const response = await this.post(`/grade1-calculations/calculate`, payload);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

     async grade2EmissionValues(payload: any): Promise<any> {
        try {
            const response = await this.post(`/grade2-calculations/calculate`, payload);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

     async grade2B4ReplCalculations(payload: any): Promise<any> {
        try {
            const response = await this.post(`/grade2-b4-replacement/calculate`, payload);
            return response.data;
        } catch (error: any) {
            console.error(error.message);
            throw error;
        }
    }

    async grade34Calculations(payload: any): Promise<any> {
        try {
            const response = await this.post(`/grade34-construction-calculations/calculate`, payload);
            return response.data;
        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }
    }


     async electricityCalculations(payload: any): Promise<any> {
        try {
            const response = await this.post(`/electricity-detailed-calculations/calculate`, payload);
            return response.data;
        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }
    }

    async useB1G2Calculations(payload: any): Promise<any> {
        try {
            const response = await this.post(`/inuse-gases-calculations/calculate`, payload);
            return response.data;
        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }       
    }


    async detailedG3Calculations(payload: any): Promise<any> {
        try{
            const response = await this.post(`/grade34-maintenance-calculations/calculate`, payload);
            return response.data;

        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }
    }


    async replDetailedG3Calculations(payload: any): Promise<any> {
        try{
            const response = await this.post(`/detailed-level-maintenance-b2-b5-calculations/calculate`, payload);
            return response.data;
        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }
    }

    async opEnergyDetailedCalculations(payload: any): Promise<any> {
        try{
            const response = await this.post(`/detailed-level-fuel-water-calculations/calculate`, payload);
            return response.data;
        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }
    }
    
    async concreteRegSimplifiedCalculations(payload: any): Promise<any> {
        try{
            const response = await this.post(`/concrete-register/calculate-simplified`, payload);
            return response.data;
        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }
    }

    async concreteRegNewMixCalculations(payload: any): Promise<any> {
        try {
            const response = await this.post(`/concrete-register/calculate`, payload);
            return response.data;
        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }
    }

    async concreteRegNewMixEPDCalculations(payload: any): Promise<any> {
        try {
            const response = await this.post(`/concrete-register/calculate-epd-shortcut`, payload);
            return response.data;
        }
        catch(err: any){
            console.error(err.message);
            throw err;
        }
    }

    async calculateNzRoads(payload: any):Promise<any> {
        try {
            const response = await this.post(`/user-emissions/nz/roads/calculate`, payload);
           return this.normalizeUserEmissionSummary(response?.data ?? response);
        }
        catch (err: any){
            console.error(err.message);
            throw err;
        }
    }

     async calculateAusRoads(payload: any):Promise<any> {
        try {
            const response = await this.post(`/user-emissions/aus/roads/calculate`, payload,  {
                timeout: 180000, // 3 minutes
            });
           return this.normalizeUserEmissionSummary(response?.data ?? response);
        }
        catch (err: any){
            console.error(err.message);
            throw err;
        }
    }

     
async calculateLargeAusRoads(payload: any): Promise<any> {
    try {
        const response = await this.post(
            `/user-emissions/aus/large/roads/calculate`,
            payload,
            {
                timeout: 180000, // 3 minutes
            }
        );
        return this.normalizeUserEmissionSummary(response?.data ?? response);
    } catch (err: any) {
        console.error(err.message);
        throw err;
    }
}

     async calculateRail(payload: any):Promise<any> {
        try {
            const response = await this.post(`/user-emissions/rail/calculate`, payload);
           return response?.data ?? response;
        }
        catch (err: any){
            console.error(err.message);
            throw err;
        }
    }

    async calculateLargeNzRoads(payload: any):Promise<any> {
        try {
            const response = await this.post(`/user-emissions/nz/large/roads/calculate`, payload);
           return this.normalizeUserEmissionSummary(response?.data ?? response);
        }
        catch (err: any){
            console.error(err.message);
            throw err;
        }
    }
}

export default new EmissionCalculationsService();