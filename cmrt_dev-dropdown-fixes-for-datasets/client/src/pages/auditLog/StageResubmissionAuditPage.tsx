import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchStageResubmissionAudit, type StageResubmissionAuditResult } from '@/services/AuditLog.service';
import { useUser } from '@/context/UserContext';
import { extractApiError } from '@/utils/utils';
import type { AuditLogRow } from '@/pages/datasets/types';
import {
  ActionBadge,
  ActivityDataChanges,
  ActivityDataNew,
  StageCell,
  SubstageCell,
  TableCell,
  type AuditMeta,
} from './AuditLogPage';

function _fmtDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const STAGE_LABELS: Record<string, string> = {
  BUSINESS_CASE: 'Business Case',
  DESIGN: 'Design',
  CONSTRUCTION: 'Construction',
  RECURRING: 'Recurring',
};

export default function StageResubmissionAuditPage() {
  const { stageInstanceId } = useParams<{ stageInstanceId: string }>();
  // const navigate = useNavigate();
  const { roles } = useUser();

  const isAllowed =
    roles.includes('PROJECT_ADMIN') ||
    roles.includes('ORG_ADMIN');

  const [result, setResult] = useState<StageResubmissionAuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!stageInstanceId || !isAllowed) return;
    setLoading(true);
    setError(null);
    fetchStageResubmissionAudit(stageInstanceId)
      .then(setResult)
      .catch((err) =>
        setError(extractApiError(err, 'Failed to load resubmission audit.')),
      )
      .finally(() => setLoading(false));
  }, [stageInstanceId, isAllowed]);

  if (!isAllowed) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-400">
        You do not have permission to view this audit log.
      </div>
    );
  }

  const stageName = result?.stage_name ? (STAGE_LABELS[result.stage_name] ?? result.stage_name) : '';
  const rows: AuditLogRow[] = result?.rows ?? [];

  return (
    <div className="min-h-full bg-bg-content">
      <div className="flex items-center gap-3 px-8 py-4 border-b border-gray-200 bg-white">
        {/* <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 cursor-pointer"
        >
          <span className="material-symbols-rounded text-base">arrow_back</span>
          Back
        </button>
        <span className="text-gray-300">|</span> */}
        <div className="text-sm font-medium text-text-dark">
          {stageName ? `${stageName} — Changes for Review` : 'Stage Audit Changes'}
        </div>
      </div>

      <div className="mx-auto w-[90%] px-4 py-6 space-y-6">

        {result?.has_prior_rejection && result.window_from && result.window_to && (
          <div className="bg-blue-50 border border-blue-200 rounded-sm px-4 py-3 text-sm text-blue-800 flex items-start gap-2">
            <span className="material-symbols-rounded text-base shrink-0 mt-0.5">info</span>
            <span>
              Showing data changes made between{' '}
              <strong>{_fmtDate(result.window_from)}</strong>
              {' '}and{' '}
              <strong>{_fmtDate(result.window_to)}</strong>
              {' '}(between last rejection / reopen and the current resubmission).
            </span>
          </div>
        )}

        <div className="bg-white border border-gray-200 rounded-sm overflow-hidden">
          {loading ? (
            <div className="flex h-40 items-center justify-center text-sm text-gray-400">
              Loading…
            </div>
          ) : error ? (
            <div className="flex h-40 items-center justify-center text-sm text-red-500">{error}</div>
          ) : !result?.has_prior_rejection ? (
            <div className="flex h-40 items-center justify-center text-sm text-gray-400 italic">
              No prior rejection or reopen found — this stage has not been reviewed before.
            </div>
          ) : rows.length === 0 ? (
            <div className="flex h-40 items-center justify-center text-sm text-gray-400 italic">
              No data changes were recorded in the resubmission window.
            </div>
          ) : (
            <div className="overflow-x-hidden overflow-y-auto max-h-[calc(100vh-18rem)]">
              <table className="w-full table-fixed border-collapse text-xs">
                <colgroup>
                  <col style={{ width: '12%' }} />
                  <col style={{ width: '9%' }} />
                  <col style={{ width: '12%' }} />
                  <col style={{ width: '10%' }} />
                  <col style={{ width: '6%' }} />
                  <col style={{ width: '14%' }} />
                  <col style={{ width: '11%' }} />
                  <col style={{ width: '26%' }} />
                </colgroup>
                <thead className="sticky top-0 z-10 bg-neutral-50 border-b border-gray-200">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">Timestamp</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">Stage</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">Substage / Reporting Period</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">Table</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">Action</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">User</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">Organisation</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-500">Before / After</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {rows.map((r) => {
                    const meta = (r.event_metadata ?? {}) as AuditMeta;
                    const fieldDiffs = meta.field_diffs ?? [];
                    return (
                      <tr key={r.id} className="even:bg-gray-50 hover:bg-blue-50 transition-colors">
                        <td className="px-3 py-2 text-gray-500">
                          {r.performed_at
                            ? new Date(r.performed_at).toLocaleString('en-AU')
                            : '—'}
                        </td>
                        <td className="px-3 py-2 overflow-hidden">
                          <StageCell row={r} />
                        </td>
                        <td className="px-3 py-2 overflow-hidden">
                          <SubstageCell row={r} />
                        </td>
                        <td className="px-3 py-2 overflow-hidden">
                          <TableCell row={r} />
                        </td>
                        <td className="px-3 py-2">
                          <ActionBadge action={r.action} />
                        </td>
                        <td className="px-3 py-2 text-gray-700 truncate">
                          {r.performed_by_email ?? r.performed_by ?? '—'}
                        </td>
                        <td className="px-3 py-2 text-gray-500 truncate">
                          {r.performed_by_org_name ?? '—'}
                        </td>
                        <td className="px-3 py-2 text-gray-500">
                          {meta.new_values ? (
                            <ActivityDataNew vals={meta.new_values} />
                          ) : meta.changes ? (
                            <ActivityDataChanges
                              changes={
                                meta.changes as Record<string, { before: unknown; after: unknown }>
                              }
                            />
                          ) : fieldDiffs.length > 0 ? (
                            <ul className="space-y-1">
                              {fieldDiffs.map((d: any, i: number) => (
                                <li key={`${d.field}-${i}`} className="text-[10px]">
                                  <span className="font-medium text-gray-600">{d.field}:</span>{' '}
                                  <span className="text-red-500 line-through">
                                    {d.old_value ?? 'null'}
                                  </span>
                                  {' → '}
                                  <span className="text-green-600">{d.new_value ?? 'null'}</span>
                                </li>
                              ))}
                            </ul>
                          ) : r.field_name ? (
                            <span className="text-[10px]">
                              <span className="font-medium text-gray-600">{r.field_name}:</span>{' '}
                              <span className="text-red-500 line-through">
                                {r.old_value ?? 'null'}
                              </span>
                              {' → '}
                              <span className="text-green-600">{r.new_value ?? 'null'}</span>
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {rows.length > 0 && (
          <p className="text-xs text-gray-400">Showing {rows.length} entries.</p>
        )}
      </div>
    </div>
  );
}
