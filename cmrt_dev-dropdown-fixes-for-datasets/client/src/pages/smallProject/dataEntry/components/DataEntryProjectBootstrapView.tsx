interface Props {
  accessDenied: boolean;
  isLoaded: boolean;
  loadError: string | null;
  onBack: () => void;
}

/** Presents the terminal loading, access, and project-load states for Data Entry. */
export function DataEntryProjectBootstrapView({
  accessDenied,
  isLoaded,
  loadError,
  onBack,
}: Props) {
  if (accessDenied) {
    return (
      <div className="flex h-full items-center justify-center bg-neutral-98 p-8">
        <div className="rounded border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h2 className="text-lg font-medium text-slate-800">No stage access</h2>
          <p className="mt-2 text-sm text-slate-500">You do not have access to any active stage in this project.</p>
          <button
            type="button"
            onClick={onBack}
            className="mt-5 rounded bg-primary px-4 py-2 text-sm font-medium text-white"
          >
            Back to project
          </button>
        </div>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="flex h-full items-center justify-center bg-neutral-98 p-8" role="status">
        Loading project data…
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex h-full items-center justify-center bg-neutral-98 p-8">
        <div className="rounded border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h2 className="text-lg font-medium text-slate-800">Project data unavailable</h2>
          <p className="mt-2 text-sm text-slate-500">{loadError}</p>
          <button
            type="button"
            onClick={onBack}
            className="mt-5 rounded bg-primary px-4 py-2 text-sm font-medium text-white"
          >
            Back to project
          </button>
        </div>
      </div>
    );
  }

  return null;
}
