import http from '@/http';

export type PartnerType = 'DESIGNERS' | 'CONTRACTORS';
export type PartnerOrganization = {
  id: string;
  name: string;
  partner_type: PartnerType;
  is_active: boolean;
};
export type PartnerSuggestion = {
  id: string;
  name: string;
  partner_type: PartnerType;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  submitted_by_user_id: string;
  partner_organization_id: string | null;
};

const partnerOrganizationsService = {
  async list(partnerType: PartnerType): Promise<PartnerOrganization[]> {
    const response = await http.get('/api/partner-organizations', {
      params: { partner_type: partnerType, limit: 500 },
    });
    return response.data;
  },
  async suggest(name: string, partnerType: PartnerType): Promise<PartnerSuggestion> {
    const response = await http.post('/api/partner-organizations/suggestions', {
      name,
      partner_type: partnerType,
    });
    return response.data;
  },
  async listPending(): Promise<PartnerSuggestion[]> {
    const response = await http.get('/api/partner-organizations/suggestions/pending');
    return response.data;
  },
  async review(id: string, decision: 'approved' | 'rejected'): Promise<PartnerSuggestion> {
    const response = await http.post(`/api/partner-organizations/suggestions/${id}/review`, { decision });
    return response.data;
  },
};

export default partnerOrganizationsService;
