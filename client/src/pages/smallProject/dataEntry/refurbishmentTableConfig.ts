import http from '@/http';

interface MrFactor {
  id: string;
  activity_type: string;
  item: string;
  unit: any;
  emissions_intensity_tco2e: number | null;
  default_frequency_years: number | null;
  jurisdiction_name: string | null;
}

type BoundaryContext = {
  boundary: any;
  existingRow?: any;
};


const _mrFactorsCache: Record<string, MrFactor[]> = {};

export async function fetchAllActiveMrFactors(jurisdictionName?: string | null): Promise<MrFactor[]> {
  const cacheKey = jurisdictionName ?? "__all__";
  if (_mrFactorsCache[cacheKey]?.length > 0) return _mrFactorsCache[cacheKey];
  try {
    const url = jurisdictionName
      ? `/api/maintenance-replacement-factors/active?jurisdiction_name=${encodeURIComponent(jurisdictionName)}`
      : '/api/maintenance-replacement-factors/active';
    const res = await http.get(url);
    _mrFactorsCache[cacheKey] = (res.data ?? []) as MrFactor[];
  } catch (e) {
    console.error('Failed to load maintenance & replacement factors:', e);
    return [];
  }
  return _mrFactorsCache[cacheKey];
}

export const refurbishmentTableConfig = (jurisdictionName?: string | null) => ({
  tableName: "Other partial replacement or refurbishment activities",
  boundary: {
  appliesTo: "Maintenance",
  createPlaceholder: ({ boundary }: BoundaryContext) => ({
    _fromBoundary: true,
    reporting_boundary_id: boundary.id,
    activityType: boundary.category,
    item: boundary.sub_category,
    unit_code: "",
    frequency: null,
    quantity: null,
    emissions_tco2e: null,
  }),
},
  calculation: {
    grade: 1 as const,
    requiredKeys: ["mr_factor_id", "quantity", "frequency"],
    triggerKeys: ["mr_factor_id", "quantity", "frequency"],
    buildPayload: (row: any, ctx: any) => {
      const cacheKey = jurisdictionName ?? "__all__";
      const factor = (_mrFactorsCache[cacheKey] ?? []).find((f) => f.id === row.mr_factor_id);
      if (!factor) return null;
      const quantity = Number(row.quantity);
      const frequency_years = Number(row.frequency);
      if (isNaN(quantity) || quantity <= 0) return null;
      if (isNaN(frequency_years) || frequency_years <= 0) return null;
      const reference_period = ctx?.reference_period;
      if (!reference_period || reference_period <= 0) return null;
      return {
        jurisdiction: factor.jurisdiction_name ?? "Australia",
        activity_type: factor.activity_type,
        item: factor.item,
        unit: factor.unit.code,
        quantity,
        reference_period,
        frequency_years,
      };
    },
    calculate: async (payload: any) => {
      const res = await http.post('/api/maintenance-calculations/calculate', payload);
      return res.data;
    },
    mapResultToRow: (apiRes: any) => {
      const v = apiRes.total_emissions_tco2e ?? null;
      return {
        emissions_tco2e: v,
        total_emissions_tco2e: v,
      };
    },
  },
  fileHeaders: [
    { key: "activityType", label: "Activity type" },
    { key: "item", label: "Item" },
    { key: "frequency", label: "Frequency (years)" },
    { key: "unit", label: "Unit" },
    { key: "quantity", label: "Quantity" },
    { key: "notes", label: "Notes/Comments (optional)" },
  ],
  rules: [
    {
      label: "Activity type",
      keySource: "activityType",
      key: "activityType",
      required: true,
      lookup: {
        fetch: async () => {
          const factors = await fetchAllActiveMrFactors(jurisdictionName);
          const types = [...new Set(factors.map((f) => f.activity_type))];
          return types.map((t) => ({ label: t, value: t }));
        },
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Item",
      keySource: "item",
      key: "mr_factor_id",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: any }) => {
          const activityType = ctx?.row?.activityType;
          if (!activityType) return [];
          const factors = await fetchAllActiveMrFactors(jurisdictionName);
          return factors
            .filter((f) => f.activity_type === activityType)
            .map((f) => ({
              label: f.item,
              value: f.id,
              _data: {
                default_frequency_years: f.default_frequency_years,
                unit_code: f.unit.code,
              },
            }));
        },
        labelField: "label",
        idField: "value",
      },
    },
    { label: "Frequency (years)", keySource: "frequency", key: "frequency", number: true, required: true },
    { label: "Quantity", keySource: "quantity", key: "quantity", number: true, required: true },
    { label: "Notes / Comments (optional)", keySource: "notes", key: "notes" },
  ],
  columns: () => [
    {
      header: "Activity type",
      width: "18%",
      key: "activityType",
      editable: true,
      // editableWhen: (row: any) => row?.id === "__NEW__",
      editorType: "select",
      idKey: "activityType",
      getOptions: async () => {
        const factors = await fetchAllActiveMrFactors(jurisdictionName);
        const types = [...new Set(factors.map((f) => f.activity_type))];
        return types.map((t) => ({ label: t, value: t }));
      },
      clearsOnChange: ["item", "mr_factor_id"],
    },
    {
      header: "Item",
      width: "22%",
      key: "item",
      editable: true,
      // editableWhen: (row: any) => row?.id === "__NEW__",
      editorType: "select",
      idKey: "mr_factor_id",
      dependsOnKeys: ["activityType"],
      getOptions: async (ctx?: { row?: any }) => {
        const activityType = ctx?.row?.activityType;
        if (!activityType) return [];
        const factors = await fetchAllActiveMrFactors(jurisdictionName);
        return factors
          .filter((f) => f.activity_type === activityType)
          .map((f) => ({
            label: f.item,
            value: f.id,
            _data: {
              default_frequency_years: f.default_frequency_years,
              unit_code: f.unit.code,
            },
          }));
      },
      onSelect: (selected: any) => selected
        ? {
          frequency: selected._data?.default_frequency_years ?? '',
          unit_code: selected._data?.unit_code ?? 'm2',
        }
        : { frequency: '', unit_code: 'm2' },
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Frequency (years)",
      width: "12%",
      key: "frequency",
      editable: true,
      editorType: "number",
    },
    {
      header: "Unit",
      width: "8%",
      key: "unit_code",
      editable: true,
      render: (row: any) => row.unit_code ?? "",
    },
    { 
      header: "Quantity", 
      width: "10%", 
      key: "quantity", 
      editable: true, 
      editorType: "number" 
    },
    { 
      header: "Emissions (tCO₂e)", 
      width: "12%", 
      key: "emissions_tco2e", 
      editable: false 
    },
    { 
      header: "Notes / Comments (optional)", 
      width: "18%", 
      key: "notes", 
      editable: true, 
      editorType: "text" 
    },
  ],
});
