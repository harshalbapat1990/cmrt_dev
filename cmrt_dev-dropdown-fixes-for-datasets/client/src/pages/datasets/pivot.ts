import type { BgmRow, G1Row, G2Row, G34Row } from './types';
import { METRIC_LABEL } from './constants';
import { toNum } from './utils';

export function pivotGrade1(rows: BgmRow[]): G1Row[] {
  const map = new Map<string, G1Row>();
  for (const r of rows) {
    const key = `${r.jurisdiction_id ?? ''}||${r.mastertype_id ?? ''}||${r.typecast_id ?? ''}||${r.metric_type_code}`;
    if (!map.has(key)) {
      map.set(key, {
        mastertype:   r.mastertype_name ?? '',
        typecast:     r.typecast_name   ?? '',
        metric:       METRIC_LABEL[r.metric_type_code ?? ''] ?? (r.metric_type_name ?? r.metric_type_code ?? ''),
        unit:         r.unit_label ?? r.unit_code ?? '',
        source:       r.source ?? '',
        jurisdiction: r.jurisdiction_name ?? '',
        low: null, mid: null, high: null,
        _low_id: null, _mid_id: null, _high_id: null,
        _unit_id: r.unit_id ?? null,
        _metric_type_id: r.metric_type_id ?? null,
        _metric_type_code: r.metric_type_code ?? null,
        _dataset_revision_id: r.dataset_revision_id ?? null,
        _grade_id: r.grade_id,
        _mastertype_id: r.mastertype_id ?? null,
        _typecast_id: r.typecast_id ?? null,
        _jurisdiction_id: r.jurisdiction_id ?? null,
      });
    }
    const g = map.get(key)!;
    const v = toNum(r.value);
    if (r.band_code === 'Low')  { g.low  = v; g._low_id  = r.id; }
    if (r.band_code === 'Mid')  { g.mid  = v; g._mid_id  = r.id; }
    if (r.band_code === 'High') { g.high = v; g._high_id = r.id; }
    if (r.source) g.source = r.source;
  }
  return Array.from(map.values());
}

export function pivotGrade2(rows: BgmRow[]): G2Row[] {
  const map = new Map<string, G2Row>();
  for (const r of rows) {
    const key = `${r.jurisdiction_id ?? ''}||${r.emissions_category}||${r.emissions_subcategory}||${r.emissions_source}||${r.unit_code}`;
    if (!map.has(key)) {
      map.set(key, {
        emissions_category:    r.emissions_category    ?? '',
        emissions_subcategory: r.emissions_subcategory ?? '',
        emissions_source:      r.emissions_source      ?? '',
        quantity: toNum(r.assumed_quantity_default),
        unit:     r.unit_label ?? r.unit_code ?? '',
        jurisdiction: r.jurisdiction_name ?? '',
        carbon_storage: null, a1_a3: null, a4: null, a5: null,
        source: r.source ?? '',
        _cs_id: null, _a1a3_id: null, _a4_id: null, _a5_id: null,
        _unit_id: r.unit_id ?? null,
        _cat_id: r.emissions_category_id ?? null,
        _subcat_id: r.emissions_subcategory_id ?? null,
        _dataset_revision_id: r.dataset_revision_id ?? null,
        _grade_id: r.grade_id,
        _jurisdiction_id: r.jurisdiction_id ?? null,
      });
    }
    const g = map.get(key)!;
    const v = toNum(r.value);
    const mt = r.metric_type_code ?? '';
    if (mt === 'carbon_storage')           { g.carbon_storage = v; g._cs_id   = r.id; }
    if (mt === 'emission_intensity_a1_a3') { g.a1_a3 = v; g._a1a3_id = r.id; }
    if (mt === 'emission_intensity_a4')    { g.a4    = v; g._a4_id   = r.id; }
    if (mt === 'emission_intensity_a5')    { g.a5    = v; g._a5_id   = r.id; }
    if (r.source) g.source = r.source;
  }
  return Array.from(map.values());
}

export function pivotGrade34(rows: BgmRow[]): G34Row[] {
  const map = new Map<string, G34Row>();
  for (const r of rows) {
    const key = `${r.jurisdiction_id ?? ''}||${r.emissions_category}||${r.emissions_subcategory}||${r.emissions_source}||${r.unit_code}`;
    if (!map.has(key)) {
      map.set(key, {
        emissions_category:    r.emissions_category    ?? '',
        emissions_subcategory: r.emissions_subcategory ?? '',
        emissions_source:      r.emissions_source      ?? '',
        unit:   r.unit_label ?? r.unit_code ?? '',
        jurisdiction: r.jurisdiction_name ?? '',
        carbon_storage: null, scope1: null, scope2: null, scope3: null,
        source: r.source ?? '',
        _cs_id: null, _s1_id: null, _s2_id: null, _s3_id: null,
        _unit_id: r.unit_id ?? null,
        _cat_id: r.emissions_category_id ?? null,
        _subcat_id: r.emissions_subcategory_id ?? null,
        _dataset_revision_id: r.dataset_revision_id ?? null,
        _grade_id: r.grade_id,
        _jurisdiction_id: r.jurisdiction_id ?? null,
      });
    }
    const g = map.get(key)!;
    const v = toNum(r.value);
    const mt = r.metric_type_code ?? '';
    const scope = r.ghg_scope_id;
    if (mt === 'carbon_storage')       { g.carbon_storage = v; g._cs_id = r.id; }
    if (mt === 'emission_factor_scope1' || scope === 1) { g.scope1 = v; g._s1_id = r.id; }
    if (mt === 'emission_factor_scope2' || scope === 2) { g.scope2 = v; g._s2_id = r.id; }
    if (mt === 'emission_factor_scope3' || scope === 3) { g.scope3 = v; g._s3_id = r.id; }
    if (r.source) g.source = r.source;
  }
  return Array.from(map.values());
}
