import { useEffect, useLayoutEffect, useState, type Dispatch, type MutableRefObject, type SetStateAction } from "react";
import { getMitigationPanelBaseKeys } from "../mitigationConstants";
import type { DataEntryRow } from "../dataEntryTypes";
import type { MitigationLifecyclePhase } from "../mitigationTypes";
import type { MitigationTablesCollector, StageName } from "../Mitigations";

export type MitigationRowState = {
  componentRows: DataEntryRow[];
  setComponentRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  bcDetailedRows: DataEntryRow[];
  setBcDetailedRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  electricityRows: DataEntryRow[];
  setElectricityRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  useB1G2Rows: DataEntryRow[];
  setUseB1G2Rows: Dispatch<SetStateAction<DataEntryRow[]>>;
  useB1G3Rows: DataEntryRow[];
  setUseB1G3Rows: Dispatch<SetStateAction<DataEntryRow[]>>;
  componentReplRows: DataEntryRow[];
  setComponentReplRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  refurbRows: DataEntryRow[];
  setRefurbRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  replDetailedRows: DataEntryRow[];
  setReplDetailedRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  opEnergyRows: DataEntryRow[];
  setOpEnergyRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  opEnergyDetailedRows: DataEntryRow[];
  setOpEnergyDetailedRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  opEnergyElectricityRows: DataEntryRow[];
  setOpEnergyElectricityRows: Dispatch<SetStateAction<DataEntryRow[]>>;
  constructionG2Rows: DataEntryRow[];
  setConstructionG2Rows: Dispatch<SetStateAction<DataEntryRow[]>>;
  constructionG3Rows: DataEntryRow[];
  setConstructionG3Rows: Dispatch<SetStateAction<DataEntryRow[]>>;
  concreteRegSimplifiedRows: DataEntryRow[];
  setConcreteRegSimplifiedRows: Dispatch<SetStateAction<DataEntryRow[]>>;
};

type Params = {
  submissionStage: StageName;
  lifecyclePhase: MitigationLifecyclePhase;
  collectorRef?: MutableRefObject<MitigationTablesCollector | null>;
  hydrateTables?: Record<string, DataEntryRow[]> | null;
};

type RowSetter = Dispatch<SetStateAction<DataEntryRow[]>>;

export function useMitigationTableRows({
  submissionStage,
  lifecyclePhase,
  collectorRef,
  hydrateTables,
}: Params): MitigationRowState {
  const [componentRows, setComponentRows] = useState<DataEntryRow[]>([]);
  const [bcDetailedRows, setBcDetailedRows] = useState<DataEntryRow[]>([]);
  const [electricityRows, setElectricityRows] = useState<DataEntryRow[]>([]);
  const [useB1G2Rows, setUseB1G2Rows] = useState<DataEntryRow[]>([]);
  const [useB1G3Rows, setUseB1G3Rows] = useState<DataEntryRow[]>([]);
  const [componentReplRows, setComponentReplRows] = useState<DataEntryRow[]>([]);
  const [refurbRows, setRefurbRows] = useState<DataEntryRow[]>([]);
  const [replDetailedRows, setReplDetailedRows] = useState<DataEntryRow[]>([]);
  const [opEnergyRows, setOpEnergyRows] = useState<DataEntryRow[]>([]);
  const [opEnergyDetailedRows, setOpEnergyDetailedRows] = useState<DataEntryRow[]>([]);
  const [opEnergyElectricityRows, setOpEnergyElectricityRows] = useState<DataEntryRow[]>([]);
  const [constructionG2Rows, setConstructionG2Rows] = useState<DataEntryRow[]>([]);
  const [constructionG3Rows, setConstructionG3Rows] = useState<DataEntryRow[]>([]);
  const [concreteRegSimplifiedRows, setConcreteRegSimplifiedRows] = useState<DataEntryRow[]>([]);

  useEffect(() => {
    if (!hydrateTables) return;
    const setters: Record<string, RowSetter> = {
      component: setComponentRows,
      bcDetailedLevel: setBcDetailedRows,
      electricity: setElectricityRows,
      useB1G2: setUseB1G2Rows,
      useB1G3: setUseB1G3Rows,
      componentRepl: setComponentReplRows,
      refurbishment: setRefurbRows,
      replDetailed: setReplDetailedRows,
      opEnergy: setOpEnergyRows,
      opEnergyDetailed: setOpEnergyDetailedRows,
      opEnergyElectricity: setOpEnergyElectricityRows,
      constructionG2: setConstructionG2Rows,
      constructionG3: setConstructionG3Rows,
      concreteRegSimplified: setConcreteRegSimplifiedRows,
    };
    for (const [key, rows] of Object.entries(hydrateTables)) {
      setters[key]?.(rows);
    }
  }, [hydrateTables]);

  useLayoutEffect(() => {
    if (!collectorRef) return;
    const rowsByKey: Record<string, DataEntryRow[]> = {
      component: componentRows,
      bcDetailedLevel: bcDetailedRows,
      electricity: electricityRows,
      useB1G2: useB1G2Rows,
      useB1G3: useB1G3Rows,
      componentRepl: componentReplRows,
      refurbishment: refurbRows,
      replDetailed: replDetailedRows,
      opEnergy: opEnergyRows,
      opEnergyDetailed: opEnergyDetailedRows,
      opEnergyElectricity: opEnergyElectricityRows,
      constructionG2: constructionG2Rows,
      constructionG3: constructionG3Rows,
      concreteRegSimplified: concreteRegSimplifiedRows,
    };
    collectorRef.current = {
      collect: () => Object.fromEntries(
        getMitigationPanelBaseKeys(submissionStage, lifecyclePhase)
          .filter((key) => key in rowsByKey)
          .map((key) => [key, rowsByKey[key]]),
      ),
    };
  }, [
    collectorRef, submissionStage, lifecyclePhase, componentRows, bcDetailedRows,
    electricityRows, useB1G2Rows, useB1G3Rows, componentReplRows, refurbRows,
    replDetailedRows, opEnergyRows, opEnergyDetailedRows, opEnergyElectricityRows,
    constructionG2Rows, constructionG3Rows, concreteRegSimplifiedRows,
  ]);

  return {
    componentRows, setComponentRows, bcDetailedRows, setBcDetailedRows,
    electricityRows, setElectricityRows, useB1G2Rows, setUseB1G2Rows,
    useB1G3Rows, setUseB1G3Rows, componentReplRows, setComponentReplRows,
    refurbRows, setRefurbRows, replDetailedRows, setReplDetailedRows,
    opEnergyRows, setOpEnergyRows, opEnergyDetailedRows, setOpEnergyDetailedRows,
    opEnergyElectricityRows, setOpEnergyElectricityRows, constructionG2Rows,
    setConstructionG2Rows, constructionG3Rows, setConstructionG3Rows,
    concreteRegSimplifiedRows, setConcreteRegSimplifiedRows,
  };
}
