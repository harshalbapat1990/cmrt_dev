import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import http from '@/http';
import { useGrade34CategoryOptions } from './useGrade34CategoryOptions';

vi.mock('@/http', () => ({ default: { get: vi.fn() } }));

const mockedGet = vi.mocked(http.get);

describe('useGrade34CategoryOptions', () => {
  beforeEach(() => mockedGet.mockReset());

  it('loads top-level categories and children for the selected category', async () => {
    mockedGet.mockImplementation(async (url = '') => ({
      data: url.includes('top_level_only=true')
        ? [{ id: 'category-1', name: 'Materials' }]
        : [{ id: 'subcategory-1', name: 'Ceilings & walls' }],
    }) as never);

    const { result, rerender } = renderHook(
      ({ categoryId, enabled }) => useGrade34CategoryOptions(categoryId, enabled),
      { initialProps: { categoryId: '', enabled: false } },
    );

    await waitFor(() => expect(result.current.categoryOptions).toEqual([
      { id: 'category-1', name: 'Materials' },
    ]));
    expect(mockedGet).toHaveBeenCalledWith('/api/emissions-categories?top_level_only=true&limit=500');

    rerender({ categoryId: 'category-1', enabled: true });
    await waitFor(() => expect(result.current.subcategoryOptions).toEqual([
      { id: 'subcategory-1', name: 'Ceilings & walls' },
    ]));
    expect(mockedGet).toHaveBeenCalledWith(
      '/api/emissions-categories?parent_category_id=category-1&limit=500',
    );
  });

  it('ignores a child-list response after the selected category changes', async () => {
    let resolveFirst!: (value: { data: Array<{ id: string; name: string }> }) => void;
    mockedGet.mockImplementation((url = '') => {
      if (url.includes('top_level_only=true')) {
        return Promise.resolve({ data: [] }) as never;
      }
      if (url.includes('parent_category_id=first')) {
        return new Promise(resolve => { resolveFirst = resolve; }) as never;
      }
      return Promise.resolve({ data: [{ id: 'child-second', name: 'Second child' }] }) as never;
    });

    const { result, rerender } = renderHook(
      ({ categoryId }) => useGrade34CategoryOptions(categoryId, true),
      { initialProps: { categoryId: 'first' } },
    );

    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith(
      '/api/emissions-categories?parent_category_id=first&limit=500',
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

    const { result } = renderHook(() => useGrade34CategoryOptions('category-1', true));
    await waitFor(() => expect(result.current.subcategoryError).toBe(
      'Could not load subcategories for this category.',
    ));
    expect(result.current.subcategoriesLoading).toBe(false);
  });
});
