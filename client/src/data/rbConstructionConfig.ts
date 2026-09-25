import LookupsService from "../services/Lookups.service";

export const rbConstructionUploadConfig = {
  fileHeaders: [
    { key: "category", label: "Emissions category" },
    { key: "subCategory", label: "Emissions sub-category" },
    { key: "source", label: "Emissions source" },
  ],

  rules: [
    {
      label: "Emissions category",
      keySource: "category",
      key: "emissions_category_id",
      required: true,
      lookup: {
        fetch: async () =>
          LookupsService.fetchBgmCategories([2]).then(list =>
            list.map(c => ({ label: c.name, value: c.id }))
          ),
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Emissions sub-category",
      keySource: "subCategory",
      key: "emissions_subcategory_id",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: any }) => {
          const catId = ctx?.row?.emissions_category_id;
          if (!catId) return [];
          return LookupsService.fetchBgmSubcategories([2], catId)
            .then(list => list.map(s => ({ label: s.name, value: s.id })));
        },
        labelField: "label",
        idField: "value",
      },
    },
    {
      label: "Emissions source",
      keySource: "source",
      key: "emissions_source_id",
      required: true,
      lookup: {
        fetch: async (ctx?: { row?: any }) => {
          const subId = ctx?.row?.emissions_subcategory_id;
          if (!subId) return [];
          return LookupsService.fetchBgmSources([2], subId)
            .then(list => list.map(s => ({ label: s.name, value: s.id })));
        },
        labelField: "label",
        idField: "value",
      },
    },
  ],
};