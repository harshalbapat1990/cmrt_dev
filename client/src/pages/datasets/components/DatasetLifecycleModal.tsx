export interface BoundProject {
  project_id: string;
  project_name: string;
}

export interface ProjectRecalculation {
  project_id: string;
  project_name: string;
  status: 'recalculated' | 'failed';
  missing_data: Array<{ entry?: string; dataset_table?: string; message?: string }>;
  calculation_errors: Array<{ entry?: string; message?: string }>;
  recalculated_count: number;
}

type Props = {
  mode: 'unpublish' | 'deprecate' | 'publish-report';
  projects?: BoundProject[];
  recalculations?: ProjectRecalculation[];
  loading?: boolean;
  error?: string;
  onClose: () => void;
  onConfirm?: () => void;
};

export default function DatasetLifecycleModal({
  mode,
  projects = [],
  recalculations = [],
  loading = false,
  error = '',
  onClose,
  onConfirm,
}: Props) {
  const isDeprecate = mode === 'deprecate';
  const isUnpublish = mode === 'unpublish';
  const blockedDeprecation = isDeprecate && projects.length > 0;
  const failedCount = recalculations.filter((item) => item.status === 'failed').length;

  const title = isUnpublish
    ? 'Move this revision to draft?'
    : isDeprecate
      ? 'Deprecate this revision?'
      : 'Project recalculation results';

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="dataset-lifecycle-title"
        className="w-full max-w-xl rounded-lg bg-white shadow-xl"
      >
        <header className="border-b border-neutral-90 px-6 py-4">
          <h2 id="dataset-lifecycle-title" className="text-lg font-semibold text-text-dark">
            {title}
          </h2>
        </header>

        <div className="max-h-[65vh] space-y-4 overflow-y-auto px-6 py-5 text-sm text-text-base">
          {isUnpublish && (
            <p>
              {projects.length > 0
                ? 'This revision is currently used by the projects below. Changes to its dataset values will recalculate emissions for these projects when the revision is published again.'
                : 'No projects are currently using this revision. Changes made in draft will be used when the revision is published.'}
            </p>
          )}

          {isDeprecate && (
            <p>
              {blockedDeprecation
                ? 'This revision cannot be deprecated while any project is using it. Change those projects to another published revision first.'
                : 'This revision is not currently used by any projects. Confirm that you want to mark it as deprecated.'}
            </p>
          )}

          {mode === 'publish-report' && (
            <p>
              {failedCount > 0
                ? `The revision was published. Recalculation failed for ${failedCount} of ${recalculations.length} bound project(s); those projects retain their previous saved results.`
                : `The revision was published and ${recalculations.length} bound project(s) were recalculated.`}
            </p>
          )}

          {(isUnpublish || isDeprecate) && projects.length > 0 && (
            <ul className="max-h-48 list-disc space-y-1 overflow-y-auto rounded border border-neutral-90 bg-neutral-98 px-8 py-3">
              {projects.map((project) => (
                <li key={project.project_id}>{project.project_name}</li>
              ))}
            </ul>
          )}

          {mode === 'publish-report' && recalculations.length > 0 && (
            <ul className="space-y-3">
              {recalculations.map((result) => (
                <li key={result.project_id} className="rounded border border-neutral-90 p-3">
                  <div className="font-medium text-text-dark">
                    {result.project_name}: {result.status === 'failed' ? 'recalculation failed' : 'recalculated'}
                  </div>
                  {result.missing_data.length > 0 && (
                    <p className="mt-1 text-amber-700">
                      {result.missing_data.length} missing-data warning(s)
                    </p>
                  )}
                  {result.calculation_errors.map((item, index) => (
                    <p key={`${result.project_id}-error-${index}`} className="mt-1 text-red-600">
                      {[item.entry, item.message].filter(Boolean).join(': ')}
                    </p>
                  ))}
                  {result.missing_data.map((item, index) => (
                    <p key={`${result.project_id}-missing-${index}`} className="mt-1 text-amber-700">
                      {[item.entry, item.dataset_table, item.message].filter(Boolean).join(': ')}
                    </p>
                  ))}
                </li>
              ))}
            </ul>
          )}

          {error && <p role="alert" className="text-red-600">{error}</p>}
        </div>

        <footer className="flex justify-end gap-2 border-t border-neutral-90 px-6 py-4">
          {mode !== 'publish-report' && !blockedDeprecation && (
            <button
              type="button"
              onClick={onConfirm}
              disabled={loading}
              className="rounded bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50"
            >
              {loading ? 'Working…' : isUnpublish ? 'Confirm and unpublish' : 'Confirm deprecation'}
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded border border-neutral-70 px-4 py-2 text-sm font-medium text-text-dark hover:bg-neutral-98 disabled:opacity-50"
          >
            {mode === 'publish-report' || blockedDeprecation ? 'Close' : 'Cancel'}
          </button>
        </footer>
      </section>
    </div>
  );
}
