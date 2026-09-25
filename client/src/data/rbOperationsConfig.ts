import http from "@/http";

export const rbOperationsUploadConfig = {
  fileHeaders: [
    { key: "group", label: "Group" },
    { key: "item", label: "Item" },
  ],

  rules: [
    {
      label: "Group",
      key: "group",
      required: true,
      lookup: {
        fetch: async () => {
          const res = await http.get("/api/operational-equipment", { params: { limit: 500 } });
          const groups = [...new Set(res.data.map((r: any) => r.group_name))];
          return groups.map(g => ({ label: g, value: g }));
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
          if (!ctx?.row?.group) return [];
          const res = await http.get("/api/operational-equipment", { params: { limit: 500 } });
          return res.data
            .filter((r: any) => r.group_name === ctx.row.group)
            .map((r: any) => ({ label: r.item, value: r.item }));
        },
        labelField: "label",
        idField: "value",
      },
    },
  ],
};