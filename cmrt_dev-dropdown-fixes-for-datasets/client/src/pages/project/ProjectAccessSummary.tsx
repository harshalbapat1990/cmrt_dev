import { getAccessLevelLabel, type ProjectAccessSummaryStage } from "./projectAccessSummaryUtils";

type Props = {
  loading: boolean;
  error: string | null;
  roleSummary: string;
  stages: ProjectAccessSummaryStage[];
};

export function ProjectAccessSummary({ loading, error, roleSummary, stages }: Props) {
  return (
    <section aria-labelledby="your-project-access-heading" className="mt-6 border-t border-gray-100 pt-5">
      <h3 id="your-project-access-heading" className="text-sm font-semibold text-text-dark">
        Your project access
      </h3>

      {loading ? (
        <p role="status" className="mt-2 text-sm text-gray-500">Loading your access…</p>
      ) : error ? (
        <p role="alert" className="mt-2 text-sm text-red-600">Unable to load your project access: {error}</p>
      ) : (
        <>
          <p className="mt-2 text-sm text-gray-600">
            Project-wide access: <span className="font-medium text-text-dark">{roleSummary}</span>
          </p>
          {stages.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">No enabled stages are configured for this project.</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-gray-500">
                    <th scope="col" className="py-2 pr-4 font-medium">Stage</th>
                    <th scope="col" className="py-2 font-medium">Your access</th>
                  </tr>
                </thead>
                <tbody>
                  {stages.map((stage) => (
                    <tr key={stage.id} className="border-b border-gray-100 last:border-0">
                      <th scope="row" className="py-2 pr-4 font-medium text-text-dark">{stage.name}</th>
                      <td className="py-2 text-gray-700">{getAccessLevelLabel(stage.access)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

export default ProjectAccessSummary;
