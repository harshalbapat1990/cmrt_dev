import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import http from '@/http';
import { useDatasetScopeJurisdiction } from './useDatasetScopeJurisdiction';
import type { DatasetScope } from '../types';

vi.mock('@/http', () => ({ default: { get: vi.fn() } }));

const mockedGet = vi.mocked(http.get);

describe('useDatasetScopeJurisdiction', () => {
  beforeEach(() => mockedGet.mockReset());

  it.each<DatasetScope>([
    { type: 'ORG', orgId: 'org-1' },
    { type: 'PROJECT', projectId: 'project-1', orgId: 'org-1' },
  ])('resolves the owner organization jurisdiction for $type scope', async (scope) => {
    mockedGet.mockResolvedValue({ data: { jurisdiction_id: 'jurisdiction-1' } } as never);
    const { result } = renderHook(() => useDatasetScopeJurisdiction(scope));

    await waitFor(() => expect(result.current).toBe('jurisdiction-1'));
    expect(mockedGet).toHaveBeenCalledWith('/api/organizations/org-1');
  });

  it('does not fetch a jurisdiction for global datasets', () => {
    const { result } = renderHook(() => useDatasetScopeJurisdiction({ type: 'DEFAULT' }));
    expect(result.current).toBeNull();
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it('leaves the default unset when the organization has no jurisdiction', async () => {
    mockedGet.mockResolvedValue({ data: { jurisdiction_id: null } } as never);
    const { result } = renderHook(() => useDatasetScopeJurisdiction({ type: 'ORG', orgId: 'org-1' }));

    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith('/api/organizations/org-1'));
    expect(result.current).toBeNull();
  });
});
