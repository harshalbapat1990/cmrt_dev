import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import DatasetsPage from './DatasetsPage';
import http from '@/http';
import { useProjectHeader } from '@/context/ProjectHeaderContext';


export default function ProjectDatasetsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { setProjectHeader, clearProjectHeader } = useProjectHeader();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(projectId));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    http.get<{
      project_name?: string;
      proponent_org_id?: string | null;
    }>(`/api/projects/${projectId}`)
      .then(({ data }) => {
        if (!cancelled) {
          setOrgId(data.proponent_org_id ?? null);
          setProjectHeader(data.project_name ?? 'Project', false, projectId);
        }
      })
      .catch(() => {
        if (!cancelled) setError('Unable to load the project organisation. Please refresh and try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      clearProjectHeader();
    };
  }, [projectId, setProjectHeader, clearProjectHeader]);

  if (!projectId) {
    return (
      <div className="flex items-center justify-center h-full text-text-base text-sm">
        No project ID provided.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-text-base text-sm">
        Loading project datasets…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-600 text-sm">
        {error}
      </div>
    );
  }

  if (!orgId) {
    return (
      <div className="flex items-center justify-center h-full text-text-base text-sm">
        No owning organisation found for this project.
      </div>
    );
  }

  return <DatasetsPage scope={{ type: 'PROJECT', projectId, orgId }} />;
}
