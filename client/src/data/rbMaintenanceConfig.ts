import http from "@/http";
import LookupsService from "@/services/Lookups.service";

async function revisionParams() {
  const dataset_revision_id = await LookupsService.resolvePublishedDefaultDatasetRevisionId();
  return { use_org_jurisdiction: true, ...(dataset_revision_id ? { dataset_revision_id } : {}) };
}

export const rbMaintenanceUploadConfig = {
  fileHeaders: [
    { key: "activityType", label: "Activity type" },
    { key: "item", label: "Item" },
  ],

  rules: [
    {
      label: "Activity type",
      key: "activityType",
      required: true,
      lookup: {
        fetch: async () => {
          const res = await http.get(
            "/api/maintenance-replacement-factors/active",
            {
              params: await revisionParams(),
            }
          );
          const types = [...new Set(res.data.map((r: any) => r.activity_type))];
          return types.map(t => ({ label: t, value: t }));
        },
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Item",
      key: "item",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: any }) => {
          const res = await http.get(
            "/api/maintenance-replacement-factors/active",
            {
              params: await revisionParams(),
            }
          );
          return res.data
            .filter((r: any) => r.activity_type === ctx?.row?.activityType)
            .map((r: any) => ({ label: r.item, value: r.item }));
        },
        labelField: "label",
        idField: "value",
      },
    },
  ],
};
