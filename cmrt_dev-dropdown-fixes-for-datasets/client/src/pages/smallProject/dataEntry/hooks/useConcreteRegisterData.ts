import { useEffect, useState } from "react";
import { ConcreteRegisterService } from "@/services/ConcreteRegister.service";
import type { EpdRow, MaterialRow, MixRow, SimplifiedRow } from "../concreteRegisterTypes";
import { mapConcreteMixes } from "../concreteRegisterMapping";

export function useConcreteRegisterData(projectId: string) {
  const [loading, setLoading] = useState(false);
  const [simplifiedRows, setSimplifiedRows] = useState<SimplifiedRow[]>([]);
  const [mixRows, setMixRows] = useState<MixRow[]>([]);
  const [materialsMap, setMaterialsMap] = useState<Record<string, MaterialRow[]>>({});
  const [epdRows, setEpdRows] = useState<EpdRow[]>([]);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setLoading(true);
    ConcreteRegisterService.listMixes(projectId)
      .then((mixes) => {
        if (cancelled) return;
        const snapshot = mapConcreteMixes(mixes);
        setSimplifiedRows(snapshot.simplifiedRows);
        setMixRows(snapshot.mixRows);
        setMaterialsMap(snapshot.materialsMap);
        setEpdRows(snapshot.epdRows);
      })
      .catch((error: unknown) => console.error("Failed to load concrete register:", error))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [projectId]);

  return {
    loading,
    simplifiedRows,
    setSimplifiedRows,
    mixRows,
    setMixRows,
    materialsMap,
    setMaterialsMap,
    epdRows,
    setEpdRows,
  };
}
