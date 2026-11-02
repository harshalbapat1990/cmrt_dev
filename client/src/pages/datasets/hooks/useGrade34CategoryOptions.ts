import { useEffect, useState } from 'react';
import http from '@/http';
import type { NamedOption } from '../types';

interface CategoryRecord {
  id: string;
  name: string;
}

function toOptions(records: CategoryRecord[]): NamedOption[] {
  return records.map(({ id, name }) => ({ id, name }));
}

/** Loads the category hierarchy used by the Grade 3/4 add-row form. */
export function useGrade34CategoryOptions(
  selectedCategoryId: string,
  enabled: boolean,
) {
  const [categoryOptions, setCategoryOptions] = useState<NamedOption[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoryError, setCategoryError] = useState('');
  const [subcategoryOptions, setSubcategoryOptions] = useState<NamedOption[]>([]);
  const [subcategoriesLoading, setSubcategoriesLoading] = useState(false);
  const [subcategoryError, setSubcategoryError] = useState('');

  useEffect(() => {
    let current = true;
    setCategoriesLoading(true);
    setCategoryError('');

    http.get<CategoryRecord[]>('/api/emissions-categories?top_level_only=true&limit=500')
      .then(({ data }) => {
        if (current) setCategoryOptions(toOptions(data));
      })
      .catch(() => {
        if (current) setCategoryError('Could not load emissions categories.');
      })
      .finally(() => {
        if (current) setCategoriesLoading(false);
      });

    return () => { current = false; };
  }, []);

  useEffect(() => {
    let current = true;
    setSubcategoryOptions([]);
    setSubcategoryError('');

    if (!enabled || !selectedCategoryId) {
      setSubcategoriesLoading(false);
      return () => { current = false; };
    }

    setSubcategoriesLoading(true);
    const query = new URLSearchParams({ parent_category_id: selectedCategoryId, limit: '500' });
    http.get<CategoryRecord[]>(`/api/emissions-categories?${query.toString()}`)
      .then(({ data }) => {
        if (current) setSubcategoryOptions(toOptions(data));
      })
      .catch(() => {
        if (current) setSubcategoryError('Could not load subcategories for this category.');
      })
      .finally(() => {
        if (current) setSubcategoriesLoading(false);
      });

    return () => { current = false; };
  }, [enabled, selectedCategoryId]);

  return {
    categoryOptions,
    categoriesLoading,
    categoryError,
    subcategoryOptions,
    subcategoriesLoading,
    subcategoryError,
  };
}
