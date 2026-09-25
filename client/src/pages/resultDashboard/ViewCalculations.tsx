import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import DataTable from "./DataTable";
import type { ColumnConfig } from "./DataTable";
import { SelectListbox } from "../../components/common/Select";

/* ================= TYPES ================= */

type Section =
  | "Emissions breakdown"
  | "Materials hotspots"
  | "Mitigation summary"
  | "Comparison by stage/period"
  | "Options Comparison"
  | "Renewable energy"
  | "Offsetting summary"
  | "Waste & recycle materials"
  | "LCA module breakdown"
  | "Rating performance";

interface ViewCalculationsLocationState {
  dataset: Record<string, any>;
  visibleSections: Section[];
  submission: string;
  intervalLabel: string;
  accountingMethod: string;
}

/* ================= SECTION → DATASET KEY ================= */

const SECTION_DATA_KEY: Record<Section, string> = {
  "Emissions breakdown": "emissionsBreakdown",
  "Materials hotspots": "materialHotspots",
  "Mitigation summary": "mitigationSummary",
  "Comparison by stage/period":
    "totalEmissionsByConstructionPeriod",
  "Options Comparison": "comparisonByOption",
  "Renewable energy": "renewableEnergySummary",
  "Offsetting summary": "offsettingSummary",
  "Waste & recycle materials": "wasteAndRecycle",
  "LCA module breakdown": "lcaModuleBreakdown",
  "Rating performance": "isCreditsSummary",
};

/* ================= DATA NORMALISATION ================= */

function getTableRows(section: Section, dataset: Record<string, any>) {
  switch (section) {
    case "Emissions breakdown":
      return dataset.emissionsBreakdown?.modules ?? [];

    case "Materials hotspots":
      return dataset.materialHotspots?.items ?? [];

    case "Mitigation summary":
      return dataset.mitigationSummary?.items ?? [];

    case "Waste & recycle materials":
      return dataset.wasteAndRecycle?.breakdown?.items ?? [];

    case "LCA module breakdown":
      return dataset.lcaModuleBreakdown?.rows ?? [];

    default:
      return [];
  }
}

/* ================= COLUMN CONFIG ================= */

function getColumnsForSection(
  section: Section
): ColumnConfig<any>[] {
  switch (section) {
    case "Emissions breakdown":
      return [
        { key: "code", label: "Module" },
        { key: "label", label: "Description" },
        {
          key: "value",
          label: "Emissions",
          align: "right",
        },
      ];

    case "Materials hotspots":
      return [
        { key: "material", label: "Material" },
        { key: "actual", label: "Actual", align: "right" },
        {
          key: "mitigation",
          label: "Mitigation",
          align: "right",
        },
      ];

    case "Mitigation summary":
      return [
        { key: "measure", label: "Mitigation measure" },
        {
          key: "reduction",
          label: "Reduction",
          align: "right",
        },
      ];

    case "Waste & recycle materials":
      return [
        { key: "label", label: "Category" },
        { key: "value", label: "Tonnes", align: "right" },
      ];

    case "LCA module breakdown":
      return [
        { key: "module", label: "Module" },
        {
          key: "emissions",
          label: "Emissions",
          align: "right",
        },
      ];

    default:
      return [];
  }
}

/* ================= COMPONENT ================= */

const ViewCalculations: React.FC = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const locationState =
    state as ViewCalculationsLocationState | null;

  /* ================= GUARD ================= */

  if (!locationState?.dataset) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-gray-500">
        <h2 className="text-lg font-medium">No data loaded</h2>
        <p className="text-sm mt-2">
          No data loaded. 
        </p>
        <p>
          To view results, start by choosing from the list
        </p>
        <button
          onClick={() => navigate("/resultsDashboard")}
          className="mt-6 px-4 py-2 rounded bg-[#E8E8E8] cursor-pointer"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  const {
    dataset,
    visibleSections,
  } = locationState;

  /* ================= AVAILABLE SECTIONS ================= */

  const availableSections = useMemo(
    () =>
      visibleSections.filter(
        (s) => dataset[SECTION_DATA_KEY[s]] != null
      ),
    [visibleSections, dataset]
  );

  const [selectedSection, setSelectedSection] =
    useState<Section | "">("");

  const rows = selectedSection
    ? getTableRows(selectedSection, dataset)
    : [];

  const columns = selectedSection
    ? getColumnsForSection(selectedSection)
    : [];

  /* ================= RENDER ================= */

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">

      {/* ================= HEADER ================= */}
      <div className="flex items-center justify-between px-12 py-4 border-b border-[#EBEBEB] bg-white">
        <div className="text-2xl font-normal text-[#3F3A38]">
          View detailed results
        </div>

        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">
            Choose a table from the list
          </span>

            <SelectListbox
        value={selectedSection}
        placeholder="Choose a table"
        options={availableSections.map((section) => ({
          label: section,
          value: section,
        }))}
        onChange={(val) =>
          setSelectedSection(val as Section)
        }
        className="w-[260px]"
      />


          {/* <button
            onClick={() => navigate("/resultsDashboard")}
            className="h-9 bg-primary px-3 text-sm text-white rounded-[var(--radius-3)]"
          >
            Back
          </button> */}
        </div>
      </div>

    

      {/* ================= CONTENT ================= */}
      <div className="flex-1 px-12 py-8">
        {!selectedSection && (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            <h2 className="text-lg font-medium">
              No table selected
            </h2>
            <p className="text-sm mt-2">
              Choose a table to view detailed results
            </p>
          </div>
        )}

        {selectedSection && (
          <DataTable
            title={selectedSection}
            columns={columns}
            rows={rows}
            // onExport={() =>
            //   //
            // }
          />
        )}
      </div>

      {/* ================= FOOTER ================= */}
      <div className="px-12 pb-6">
        <button
          onClick={() => navigate("/resultsDashboard")}
          className="inline-flex items-center gap-1 text-sm cursor-pointer text-[#61605F]"
        >
          <span className="material-symbols-rounded">close</span>
          Close
        </button>
      </div>
    </div>
  );
};

export default ViewCalculations;
