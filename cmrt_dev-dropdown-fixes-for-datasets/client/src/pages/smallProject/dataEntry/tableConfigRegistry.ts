import { assetTableConfig } from "./assetConfig";
import { componentTableConfig } from "./componentConfig";
import { refurbishmentTableConfig } from "./refurbishmentTableConfig";
import { componentReplacementConfig } from "./componentReplacementConfig";
import { opEnergyTableConfig } from "./opEnergyTableConfig";
import { constructionG2Config } from "./constructionG2Config";
import { constructionG3Config } from "./constructionG3Config";
import { electricityConfig } from "./electricityConfig";
import { createB1G2Config } from "./useB1G2Config";
import { createB1G3Config } from "./useB1G3Config";
import { concreteRegSimplifiedConfig } from "./ConcreteRegSimplifiedConfig";
import { concreteRegDetailedConfig } from "./concreteRegDetailedConfig";
import { electricityBaseTableKey, type UploadKey } from "./stageConstants";
import type { FieldRule } from "@/utils/ValidateRows";
import type { FileHeader } from "@/utils/parseFileToRows";

export interface DataEntryTableConfig {
  calculation?: unknown;
  rules?: FieldRule[];
  fileHeaders?: FileHeader[];
}

type TableConfigFactory = (projectId: string) => DataEntryTableConfig;
type TableConfigEntry = DataEntryTableConfig | TableConfigFactory;

export const TABLE_CONFIGS: Record<UploadKey, TableConfigEntry> = {
  asset: (projectId: string) => assetTableConfig(projectId),
  component: (projectId: string) => componentTableConfig(projectId),
  componentRepl: (projectId: string) => componentReplacementConfig(projectId),
  refurbishment: () => refurbishmentTableConfig(null),
  replDetailed: (projectId: string) => createB1G3Config(projectId),
  opEnergy: opEnergyTableConfig,
  opEnergyDetailed: (projectId: string) => createB1G3Config(projectId, ["Fuels", "Water"]),
  opEnergyElectricity: electricityConfig,
  constructionG2: (projectId: string) => constructionG2Config(projectId),
  constructionG3: (projectId: string) => constructionG3Config(projectId),
  bcDetailedLevel: (projectId: string) => constructionG3Config(projectId),
  electricity: electricityConfig,
  useB1G2: (projectId: string) => createB1G2Config(null, projectId),
  useB1G3: (projectId: string) => createB1G3Config(projectId),
  concreteRegSimplified: concreteRegSimplifiedConfig,
  concreteRegDetailed: concreteRegDetailedConfig,
  recurringG3: (projectId: string) => constructionG3Config(projectId),
};

export const resolveTableConfig = (tableKey: UploadKey, projectId: string): DataEntryTableConfig => {
  const baseKey = electricityBaseTableKey(tableKey) ?? tableKey;
  const config = TABLE_CONFIGS[baseKey];
  return typeof config === "function" ? config(projectId) : config;
};

export const normalizeRules = (rules: FieldRule[] = []): FieldRule[] =>
  rules.map((rule) => {
    const lookup = rule.lookup;
    if (!lookup?.fetch) return rule;
    return {
      ...rule,
      lookup: {
        ...lookup,
        fetch: async (context?: Parameters<typeof lookup.fetch>[0]) => {
          const result = await lookup.fetch(context);
          return Array.isArray(result) ? result : [];
        },
      },
    };
  });
