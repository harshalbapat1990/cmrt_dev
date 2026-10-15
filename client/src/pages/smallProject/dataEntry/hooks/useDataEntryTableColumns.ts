import { useMemo } from "react";
import { ACTIVITY_CATEGORY_MAP } from "@/components/ReportingBoundaryActivity";
import { assetTableConfig } from "../assetConfig";
import { componentTableConfig } from "../componentConfig";
import { refurbishmentTableConfig } from "../refurbishmentTableConfig";
import { componentReplacementConfig } from "../componentReplacementConfig";
import { opEnergyTableConfig } from "../opEnergyTableConfig";
import { constructionG2Config } from "../constructionG2Config";
import { constructionG3Config } from "../constructionG3Config";
import { electricityConfig } from "../electricityConfig";
import { createB1G2Config } from "../useB1G2Config";
import { createB1G3Config } from "../useB1G3Config";
import { concreteRegSimplifiedConfig } from "../ConcreteRegSimplifiedConfig";
import { concreteRegDetailedConfig } from "../concreteRegDetailedConfig";

/** Builds the column models used by the stage and recurring data-entry tables. */
export function useDataEntryTableColumns(projectId: string, jurisdiction: string | null) {
    const assetColumns = useMemo(() => assetTableConfig(projectId).columns(), [projectId]);
    const componentColumns = useMemo(() => componentTableConfig(projectId).columns(), [projectId]);
    const componentReplColumns = useMemo(() => componentReplacementConfig(projectId).columns(), [projectId]);
    const refurbColumns = useMemo(() => refurbishmentTableConfig(jurisdiction).columns(), [jurisdiction]);
    const opEnergyColumns = useMemo(() => opEnergyTableConfig(projectId).columns(), [projectId]);
    const opEnergyDetailedColumns = useMemo(() => createB1G3Config(projectId, ["Fuels", "Water"]).columns(), [projectId]);
    const opEnergyElectricityColumns = useMemo(() => electricityConfig(projectId).columns(), [projectId]);
    const constructionG2Columns = useMemo(() => constructionG2Config(projectId).columns(), [projectId]);
    const constructionG3Columns = useMemo(() => constructionG3Config(projectId, "constructionG3").columns(), [projectId]);
    const bcDetailedColumns = useMemo(() => constructionG3Config(projectId, "bcDetailedLevel").columns(), [projectId]);
    const electricityColumns = useMemo(() => electricityConfig(projectId).columns(), [projectId]);
    const useB1G2Columns = useMemo(() => createB1G2Config(jurisdiction, projectId).columns(), [jurisdiction, projectId]);
    const useB1G3Columns = useMemo(() => createB1G3Config(projectId, ["Gases"]).columns(), [projectId]);
    const concreteRegSimplifiedColumns = useMemo(() => concreteRegSimplifiedConfig().columns(), []);
    const concreteRegDetailedColumns = useMemo(() => concreteRegDetailedConfig().columns(), []);
    const replDetailedColumns = useMemo(() => createB1G3Config(projectId).columns(), [projectId]);

    const columnsForRecurringActivity = (activity: string) =>
        constructionG3Config(projectId, "recurringG3", ACTIVITY_CATEGORY_MAP[activity]).columns();

    return {
        assetColumns,
        componentColumns,
        componentReplColumns,
        refurbColumns,
        opEnergyColumns,
        opEnergyDetailedColumns,
        opEnergyElectricityColumns,
        constructionG2Columns,
        constructionG3Columns,
        bcDetailedColumns,
        electricityColumns,
        useB1G2Columns,
        useB1G3Columns,
        concreteRegSimplifiedColumns,
        concreteRegDetailedColumns,
        replDetailedColumns,
        columnsForRecurringActivity,
    };
}
