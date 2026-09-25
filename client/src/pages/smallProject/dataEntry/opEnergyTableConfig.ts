import http from '@/http';
import { formatEmissionsOrQuantity } from '@/utils/utils';

interface OperationalEquipment {
  id: string;
  group_name: string;
  item: string;
  power_kw: number | null;
  hours_per_day: number | null;
  days_per_year: number | null;
  is_active: boolean;
}

type BoundaryContext = {
  boundary: any;
  existingRow?: any;
};


const _opEquipCacheByProject: Record<string, OperationalEquipment[] | null> = {};

async function fetchActiveOperationalEquipment(projectId?: string): Promise<OperationalEquipment[]> {
  const cacheKey = projectId ? String(projectId) : '__global__';
  const cached = _opEquipCacheByProject[cacheKey];
  if (cached && cached.length > 0) return cached;
  try {
    const params: Record<string, any> = { limit: 500 };
    if (projectId) {
      params.project_id = projectId;
    }
    const res = await http.get('/api/operational-equipment', { params });
    _opEquipCacheByProject[cacheKey] = (res.data ?? []) as OperationalEquipment[];
  } catch (e) {
    console.error('Failed to load operational equipment:', e);
    _opEquipCacheByProject[cacheKey] = null;
    return [];
  }
  return _opEquipCacheByProject[cacheKey] ?? [];
}

export const opEnergyTableConfig = (projectId: any) => ({
  tableName: "Component level (grade 2)",

boundary: {
  appliesTo: "Operations",
  createPlaceholder: ({ boundary}: BoundaryContext ) => ({
    _fromBoundary: true,
    reporting_boundary_id: boundary.id,
    group_name: boundary.category,
    item: boundary.sub_category,
    unit_code: "Each",   
    eq_id: null,
    quantity: null,
    emissions_tco2e: null,
  }),
},

  calculation: {
    grade: 2,
    requiredKeys: ["item", "quantity"],
    triggerKeys: ["item", "quantity"],
    buildPayload: (row: any, ctx: any) => {
      if (!row.item || !row.quantity) return null;
      const opsStart = ctx.ops_start_year;
      const opsLife = ctx.reference_period;
      if (!opsStart || !opsLife) return null;
      const opsEnd = Math.min(opsStart + opsLife, 2100);
      return {
        jurisdiction: ctx.jurisdiction || "Australia",
        // region: ctx.region || "New South Wales",
        ops_start: opsStart,
        ops_end: opsEnd,
        emissions_source: row.item,
        unit: "Each",
        quantity: Number(row.quantity),
        emission_source_type: "Grid Electricity",
        emissions_category: "Operational Energy (B6)",
        emissions_sub_category: "Electricity",
        project_id: projectId,
      };
    },
    calculate: async (payload: any) => {
      const res = await http.post('/api/operational-calculations/calculate', payload);
      return res.data;
    },
    mapResultToRow: (apiRes: any) => ({
      location_based_total_tco2e: apiRes.location_based_total_tco2e ?? null,
      market_based_total_tco2e: apiRes.market_based_total_tco2e ?? null,
      scope2_location_based_tco2e: apiRes.scope2_location_based_tco2e ?? null,
      scope2_market_based_tco2e: apiRes.scope2_market_based_tco2e ?? null,
      scope3_location_based_tco2e: apiRes.scope3_location_based_tco2e ?? null,
      scope3_market_based_tco2e: apiRes.scope3_market_based_tco2e ?? null,
      emissions_tco2e: apiRes.location_based_total_tco2e ?? null,
    }),
  },

  fileHeaders: [
    { key: "group_name", label: "Group" },
    { key: "item", label: "Item" },
    { key: "quantity", label: "Quantity" },
    { key: "notes", label: "Notes/Comments (optional)" },
  ],

  rules: [
    {
      label: "Group",
      keySource: "group_name",
      key: "group_name",
      required: true,
      lookup: {
        fetch: async () => {
          const equip = await fetchActiveOperationalEquipment(projectId);
          const groups = [...new Set(equip.map((e) => e.group_name))];
          return groups.map((g) => ({ label: g, value: g }));
        },
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Item",
      keySource: "item",
      key: "item",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: any }) => {
          const group = ctx?.row?.group_name;
          if (!group) return [];
          const equip = await fetchActiveOperationalEquipment(projectId);
          return equip
            .filter((e) => e.group_name === group)
            .map((e) => ({ label: e.item, value: e.id }));
        },
        labelField: "label",
        idField: "value",
      },
    },
    { label: "Quantity", keySource: "quantity", key: "quantity", number: true, required: true },
    { label: "Notes / Comments (optional)", keySource: "notes", key: "notes" },
  ],

  columns: () => [
    // {
    //   header: "Emissions Category",
    //   key: "emissions_category",
    //   editable: true,
    //   editableWhen: (row: any) => row?.id === "__NEW__",
    //   editorType: "select",
    //   defaultValue: "Electricity",
    //   getOptions: async () => [
    //     { label: "Electricity", value: "Electricity" },
    //   ],
    //   render: (row: any) => row?.emissions_category ?? "Electricity",
    // },
    {
      header: "Group",
      width: "18%",
      key: "group_name",
      editable: true,
      // editableWhen: (row: any) => row?.id === "__NEW__",
      editorType: "select",
      getOptions: async () => {
        const equip = await fetchActiveOperationalEquipment(projectId);
        const groups = [...new Set(equip.map((e) => e.group_name))];
        return groups.map((g) => ({ label: g, value: g }));
      },
      clearsOnChange: ["item", "eq_id"],
    },
    {
      header: "Item",
      width: "24%",
      key: "item",
      editable: true,
      // editableWhen: (row: any) => row?.id === "__NEW__",
      editorType: "select",
      idKey: "eq_id",
      dependsOnKeys: ["group_name"],
      getOptions: async (ctx?: { row?: any }) => {
        const group = ctx?.row?.group_name;
        if (!group) return [];
        const equip = await fetchActiveOperationalEquipment(projectId);
        return equip
          .filter((e) => e.group_name === group)
          .map((e) => ({ label: e.item, value: e.id }));
      },
      onSelect: (_selected: any) => ({ unit_code: "Each" }),
      noCache: true,
      refreshOnDepsChange: true,
    },
    {
      header: "Unit",
      width: "8%",
      key: "unit_code",
      editable: true,
      editorType: "select",
      defaultValue: "Each",
      getOptions: async () => [
        { label: "Each", value: "Each" },
      ],
      render: (row: any) => row?.unit_code ?? "Each",
    },
    {
      header: "Quantity",
      width: "10%",
      key: "quantity",
      editable: true,
      editorType: "number",
    },
    {
      header: "Location-Based Emissions (tCO₂e)",
      width: "18%",
      key: "location_based_total_tco2e",
      editable: false,
      render: (row: any) => formatEmissionsOrQuantity(row.location_based_total_tco2e),
    },
    {
      header: "Market-Based Emissions (tCO₂e)",
      width: "18%",
      key: "market_based_total_tco2e",
      editable: false,
      render: (row: any) => formatEmissionsOrQuantity(row.market_based_total_tco2e),
    },
    // Hidden scope breakdown columns — stored for dashboard/LCA use but not shown in the UI
    // {
    //   header: "LB Scope 2 (tCO₂e)",
    //   key: "scope2_location_based_tco2e",
    //   editable: false,
    //   hidden: true,
    // },
    // {
    //   header: "MB Scope 2 (tCO₂e)",
    //   key: "scope2_market_based_tco2e",
    //   editable: false,
    //   hidden: true,
    // },
    // {
    //   header: "LB Scope 3 (tCO₂e)",
    //   key: "scope3_location_based_tco2e",
    //   editable: false,
    //   hidden: true,
    // },
    // {
    //   header: "MB Scope 3 (tCO₂e)",
    //   key: "scope3_market_based_tco2e",
    //   editable: false,
    //   hidden: true,
    // },
    {
      header: "Notes / Comments (optional)",
      width: "4%",
      key: "notes",
      editable: true,
      editorType: "text",
    },
  ],
});
