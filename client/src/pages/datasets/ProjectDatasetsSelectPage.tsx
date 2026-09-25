import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import http from '@/http';

interface Project {
  id: string;
  project_name: string;
}

export default function ProjectDatasetsSelectPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    http.get<Project[]>('/api/me/projects')
      .then(res => setProjects(res.data))
      .catch(() => setError('Failed to load your projects.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-text-base text-sm">
        Loading projects…
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

  if (projects.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-base text-sm">
        You don't have access to any projects yet.
      </div>
    );
  }

  return (
    <div className="px-8 py-8 max-w-2xl">
      <h1 className="text-xl font-semibold text-text-dark mb-1">Project Datasets</h1>
      <p className="text-sm text-text-base mb-6">
        Select a project to view and manage its dataset customisations.
      </p>
      <div className="flex flex-col gap-3">
        {projects.map(p => (
          <Link
            key={p.id}
            to={`/datasets/project/${p.id}`}
            className="flex items-center justify-between rounded border border-neutral-80 bg-white px-5 py-4 hover:border-primary hover:bg-primary/5 transition-colors group"
          >
            <span className="text-sm font-medium text-text-dark group-hover:text-primary">
              {p.project_name}
            </span>
            <span className="material-symbols-rounded text-[18px] text-text-base group-hover:text-primary">
              chevron_right
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
