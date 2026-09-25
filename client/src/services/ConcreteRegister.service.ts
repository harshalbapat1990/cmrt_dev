import BaseService from './base.service';

export type ConcreteMethod = 'simplified' | 'mix_design' | 'epd_pcf';

export interface ConcreteMixMaterialOut {
  id: string;
  concrete_mix_id: string;
  material_name: string;
  quantity_kg_m3: number | null;
  carbon_factor: number | null;
  sort_order: number;
  created_on: string | null;
  updated_on: string | null;
}

export interface ConcreteMixOut {
  id: string;
  project_id: string;
  method: ConcreteMethod;
  mix_type: string | null;
  strength_mpa: number | null;
  scm_pct: number | null;
  mix_id_label: string | null;
  gwp_a1a3: number | null;
  volume_m3: number | null;
  emissions_tco2e: number;
  notes: string | null;
  sort_order: number;
  materials: ConcreteMixMaterialOut[];
  created_on: string | null;
  updated_on: string | null;
}

export interface ConcreteMixCreate {
  project_id: string;
  method: ConcreteMethod;
  mix_type?: string | null;
  strength_mpa?: number | null;
  scm_pct?: number | null;
  mix_id_label?: string | null;
  gwp_a1a3?: number | null;
  volume_m3?: number | null;
  emissions_tco2e?: number;
  notes?: string | null;
  sort_order?: number;
}

export interface ConcreteMixUpdate {
  mix_type?: string | null;
  strength_mpa?: number | null;
  scm_pct?: number | null;
  mix_id_label?: string | null;
  gwp_a1a3?: number | null;
  volume_m3?: number | null;
  emissions_tco2e?: number | null;
  notes?: string | null;
  sort_order?: number | null;
}

export interface ConcreteMixMaterialCreate {
  concrete_mix_id: string;
  material_name?: string;
  quantity_kg_m3?: number | null;
  carbon_factor?: number | null;
  sort_order?: number;
}

export interface ConcreteMixMaterialUpdate {
  material_name?: string | null;
  quantity_kg_m3?: number | null;
  carbon_factor?: number | null;
  sort_order?: number | null;
}

class ConcreteRegisterServiceClass extends BaseService {
  constructor() {
    super('/api/concrete-register');
  }

  async listMixes(projectId: string, method?: ConcreteMethod): Promise<ConcreteMixOut[]> {
    const qs = method
      ? `?project_id=${projectId}&method=${method}`
      : `?project_id=${projectId}`;
    const response = await this.get(`/mixes${qs}`);
    return response.data;
  }

  async createMix(payload: ConcreteMixCreate): Promise<ConcreteMixOut> {
    const response = await this.post('/mixes', payload);
    return response.data;
  }

  async updateMix(mixId: string, payload: ConcreteMixUpdate): Promise<ConcreteMixOut> {
    const response = await this.patch(`/mixes/${mixId}`, payload);
    return response.data;
  }

  async deleteMix(mixId: string): Promise<void> {
    await this.delete(`/mixes/${mixId}`);
  }

  async createMaterial(mixId: string, payload: ConcreteMixMaterialCreate): Promise<ConcreteMixMaterialOut> {
    const response = await this.post(`/mixes/${mixId}/materials`, payload);
    return response.data;
  }

  async updateMaterial(materialId: string, payload: ConcreteMixMaterialUpdate): Promise<ConcreteMixMaterialOut> {
    const response = await this.patch(`/materials/${materialId}`, payload);
    return response.data;
  }

  async deleteMaterial(materialId: string): Promise<void> {
    await this.delete(`/materials/${materialId}`);
  }
}

export const ConcreteRegisterService = new ConcreteRegisterServiceClass();
