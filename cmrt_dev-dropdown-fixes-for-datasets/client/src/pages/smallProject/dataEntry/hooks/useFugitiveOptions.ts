import { useEffect } from "react";
import http from "@/http";
import LookupsService from "@/services/Lookups.service";
import type { FugitiveOption, ProjectClass } from "../dataEntryTypes";

interface Params {
    enabled: boolean;
    isUseStage: boolean;
    projectClass: ProjectClass | null;
    projectId: string;
    setFugitiveOptions: (options: FugitiveOption[]) => void;
}

export function useFugitiveOptions({ enabled, isUseStage, projectClass, projectId, setFugitiveOptions }: Params): void {
    useEffect(() => {
        if (!enabled || !isUseStage || projectClass !== "LARGE") return;
        let cancelled = false;
        void (async () => {
            try {
                const datasetRevisionId = projectId
                    ? await LookupsService.resolveProjectDatasetRevisionId(projectId)
                    : null;
                if (!datasetRevisionId) {
                    if (!cancelled) setFugitiveOptions([]);
                    return;
                }
                const response = await http.get("/api/fugitives", {
                    params: { limit: 500, dataset_revision_id: datasetRevisionId, global_only: false },
                });
                if (!cancelled) setFugitiveOptions(Array.isArray(response.data) ? response.data : []);
            } catch (error) {
                console.warn("Failed to load fugitive list:", error);
            }
        })();
        return () => { cancelled = true; };
    }, [enabled, isUseStage, projectClass, projectId, setFugitiveOptions]);
}
