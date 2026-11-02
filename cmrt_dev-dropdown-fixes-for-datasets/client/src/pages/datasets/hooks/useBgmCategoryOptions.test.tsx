import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import http from '@/http';
import { useBgmCategoryOptions } from './useBgmCategoryOptions';

vi.mock('@/http', () => ({ default: { get: vi.fn() } }));

const mockedGet = vi.mocked(http.get);

describe('useBgmCategoryOptions', () => {
  beforeEach(() => mockedGet.mockReset());

  it('loads distinct categories and children scoped to the selected revision and grade', async () => {
    mockedGet.mockImplementation(async (url = '') => ({ data: url.includes('bgm-categories')
      ? [{ id: 'category-1', name: 'Materials' }]
      : [{ id: 'subcategory-1', name: 'Ceilings & walls' }],
    }) as never);

    const { result, rerender } = renderHook(
      ({ categoryId, revisionId, gradeId, enabled }) => useBgmCategoryOptions(categoryId, revisionId, gradeId, enabled),
      { initialProps: { categoryId: '', revisionId: 'revision-1', gradeId: '3', enabled: true } },
    );

    await waitFor(() => expect(result.current.categoryOptions).toEqual([
      { id: 'category-1', name: 'Materials' },
    ]));
    expect(mockedGet).toHaveBeenCalledWith(
      '/api/lookup/bgm-categories?grade_ids=3&dataset_revision_id=revision-1',
    );

    rerender({ categoryId: 'category-1', revisionId: 'revision-1', gradeId: '3', enabled: true });
    await waitFor(() => expect(result.current.subcategoryOptions).toEqual([
      { id: 'subcategory-1', name: 'Ceilings & walls' },
    ]));
    expect(mockedGet).toHaveBeenCalledWith(
      '/api/lookup/bgm-subcategories?grade_ids=3&category_id=category-1&dataset_revision_id=revision-1',
    );
  });

  it('ignores a child-list response after the selected category changes', async () => {
    let resolveFirst!: (value: { data: Array<{ id: string; name: string }> }) => void;
    mockedGet.mockImplementation((url = '') => {
      if (url.includes('bgm-categories')) {
        return Promise.resolve({ data: [] }) as never;
      }
      if (url.includes('category_id=first')) {
        return new Promise(resolve => { resolveFirst = resolve; }) as never;
      }
      return Promise.resolve({ data: [{ id: 'child-second', name: 'Second child' }] }) as never;
    });

    const { result, rerender } = renderHook(
      ({ categoryId }) => useBgmCategoryOptions(categoryId, 'revision-1', '4', true),
      { initialProps: { categoryId: 'first' } },
    );

    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith(
      '/api/lookup/bgm-subcategories?grade_ids=4&category_id=first&dataset_revision_id=revision-1',
    ));
    rerender({ categoryId: 'second' });
    await waitFor(() => expect(result.current.subcategoryOptions).toEqual([
      { id: 'child-second', name: 'Second child' },
    ]));

    act(() => resolveFirst({ data: [{ id: 'child-first', name: 'First child' }] }));
    await waitFor(() => expect(result.current.subcategoryOptions).toEqual([
      { id: 'child-second', name: 'Second child' },
    ]));
  });

  it('exposes a readable error when the subcategory request fails', async () => {
    mockedGet
      .mockResolvedValueOnce({ data: [] } as never)
      .mockRejectedValueOnce(new Error('request failed'));

    const { result } = renderHook(() => useBgmCategoryOptions('category-1', 'revision-1', '3', true));
    await waitFor(() => expect(result.current.subcategoryError).toBe(
      'Could not load subcategories for this category.',
    ));
    expect(result.current.subcategoriesLoading).toBe(false);
  });

  it('does not issue an unscoped lookup without a selected revision or supported grade', async () => {
    const { rerender } = renderHook(
      ({ revisionId, gradeId }) => useBgmCategoryOptions('', revisionId, gradeId, true),
      { initialProps: { revisionId: '', gradeId: '3' } },
    );
    expect(mockedGet).not.toHaveBeenCalled();

    rerender({ revisionId: 'revision-1', gradeId: '1' });
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it('reloads categories and subcategories when revision or grade changes', async () => {
    mockedGet.mockResolvedValue({ data: [] } as never);
    const { rerender } = renderHook(
      ({ revisionId, gradeId }) => useBgmCategoryOptions('category-1', revisionId, gradeId, true),
      { initialProps: { revisionId: 'revision-1', gradeId: '3' } },
    );
    await waitFor(() => expect(mockedGet).toHaveBeenCalledTimes(2));

    rerender({ revisionId: 'revision-2', gradeId: '4' });
    await waitFor(() => expect(mockedGet).toHaveBeenCalledTimes(4));
    expect(mockedGet).toHaveBeenLastCalledWith(
      '/api/lookup/bgm-subcategories?grade_ids=4&category_id=category-1&dataset_revision_id=revision-2',
    );
  });

  it('supports Grade 2 lookups with the same revision-scoped filters', async () => {
    mockedGet.mockResolvedValue({ data: [] } as never);
    renderHook(() => useBgmCategoryOptions('category-2', 'revision-2', '2', true));
    await waitFor(() => expect(mockedGet).toHaveBeenCalledTimes(2));
    expect(mockedGet).toHaveBeenNthCalledWith(
      1,
      '/api/lookup/bgm-categories?grade_ids=2&dataset_revision_id=revision-2',
    );
    expect(mockedGet).toHaveBeenNthCalledWith(
      2,
      '/api/lookup/bgm-subcategories?grade_ids=2&category_id=category-2&dataset_revision_id=revision-2',
    );
  });
});
