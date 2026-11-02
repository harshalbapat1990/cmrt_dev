import { useCallback, useEffect, useMemo, useState } from "react";
import ProjectAccessService from "@/services/ProjectAccess.service";
import {
  getStageAccessLevel,
  hasAtLeastStageAccess,
  type MyProjectAccess,
  type StageAccess,
  type StageAccessLevel,
} from "@/types/authorization";

export function useProjectStageAccess(projectId?: string) {
  const [access, setAccess] = useState<MyProjectAccess | null>(null);
  const [loading, setLoading] = useState(Boolean(projectId));
  const [error, setError] = useState<unknown>(null);

  const reload = useCallback(async () => {
    if (!projectId) {
      setAccess(null);
      setLoading(false);
      setError(null);
      return null;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await ProjectAccessService.fetchMyProjectAccess(projectId);
      setAccess(result);
      return result;
    } catch (err) {
      setAccess(null);
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;

    if (!projectId) {
      setAccess(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    ProjectAccessService.fetchMyProjectAccess(projectId)
      .then((result) => {
        if (!cancelled) setAccess(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setAccess(null);
          setError(err);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const stageAccess = useMemo<StageAccess[]>(
    () => access?.stage_access ?? [],
    [access],
  );

  const stageAccessById = useMemo(
    () => new Map(stageAccess.map((item) => [item.stage_instance_id, item])),
    [stageAccess],
  );

  const getAccess = useCallback(
    (stageInstanceId?: string | null): StageAccessLevel => {
      if (!stageInstanceId) return "NONE";
      return getStageAccessLevel(stageAccessById.get(stageInstanceId));
    },
    [stageAccessById],
  );

  const canView = useCallback(
    (stageInstanceId?: string | null) =>
      hasAtLeastStageAccess(stageAccessById.get(stageInstanceId ?? ""), "VIEW"),
    [stageAccessById],
  );

  const canEdit = useCallback(
    (stageInstanceId?: string | null) =>
      hasAtLeastStageAccess(stageAccessById.get(stageInstanceId ?? ""), "EDIT"),
    [stageAccessById],
  );

  const canAdmin = useCallback(
    (stageInstanceId?: string | null) =>
      hasAtLeastStageAccess(stageAccessById.get(stageInstanceId ?? ""), "ADMIN"),
    [stageAccessById],
  );

  const isStageAccessible = useCallback(
    (stageInstanceId?: string | null) => getAccess(stageInstanceId) !== "NONE",
    [getAccess],
  );

  return {
    access,
    error,
    loading,
    ready: !loading,
    reload,
    effectiveRoles: access?.effective_roles ?? [],
    stageAccess,
    stageAccessById,
    getAccess,
    canView,
    canEdit,
    canAdmin,
    isStageAccessible,
  };
}
