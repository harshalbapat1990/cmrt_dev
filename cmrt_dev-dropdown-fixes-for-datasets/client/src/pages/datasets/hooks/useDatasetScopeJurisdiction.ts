import { useEffect, useState } from 'react';
import http from '@/http';
import type { DatasetScope } from '../types';

interface OrganizationJurisdictionResponse {
  jurisdiction_id: string | null;
}

/** Resolves the jurisdiction associated with the dataset's owning organization. */
export function useDatasetScopeJurisdiction(scope: DatasetScope): string | null {
  const organizationId = scope.type === 'ORG' || scope.type === 'PROJECT'
    ? scope.orgId
    : null;
  const [jurisdictionId, setJurisdictionId] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setJurisdictionId(null);
    if (!organizationId) return () => { current = false; };

    http.get<OrganizationJurisdictionResponse>(`/api/organizations/${encodeURIComponent(organizationId)}`)
      .then(({ data }) => {
        if (current) setJurisdictionId(data.jurisdiction_id ?? null);
      })
      .catch(() => {
        if (current) setJurisdictionId(null);
      });

    return () => { current = false; };
  }, [organizationId]);

  return jurisdictionId;
}
