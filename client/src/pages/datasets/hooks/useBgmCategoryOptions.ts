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

/** Loads category options present in the selected active BGM grade and revision. */
export function useBgmCategoryOptions(
  selectedCategoryId: string,
  datasetRevisionId: string,
  gradeId: string,
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

    setCategoryOptions([]);
    setSubcategoryOptions([]);
    setSubcategoryError('');
    if (!enabled || !datasetRevisionId || !['2', '3', '4'].includes(gradeId)) {
      setCategoriesLoading(false);
      setCategoryError('');
      setSubcategoriesLoading(false);
      return () => { current = false; };
    }

    setCategoriesLoading(true);
    setCategoryError('');

    const query = new URLSearchParams({
      grade_ids: gradeId,
      dataset_revision_id: datasetRevisionId,
    });
    http.get<CategoryRecord[]>(`/api/lookup/bgm-categories?${query.toString()}`)
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
  }, [datasetRevisionId, enabled, gradeId]);

  useEffect(() => {
    let current = true;
    setSubcategoryOptions([]);
    setSubcategoryError('');

    if (!enabled || !datasetRevisionId || !['2', '3', '4'].includes(gradeId) || !selectedCategoryId) {
      setSubcategoriesLoading(false);
      return () => { current = false; };
    }

    setSubcategoriesLoading(true);
    const query = new URLSearchParams({
      grade_ids: gradeId,
      category_id: selectedCategoryId,
      dataset_revision_id: datasetRevisionId,
    });
    http.get<CategoryRecord[]>(`/api/lookup/bgm-subcategories?${query.toString()}`)
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
  }, [datasetRevisionId, enabled, gradeId, selectedCategoryId]);

  return {
    categoryOptions,
    categoriesLoading,
    categoryError,
    subcategoryOptions,
    subcategoriesLoading,
    subcategoryError,
  };
}
