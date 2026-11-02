import { useCallback, useEffect, useState } from 'react';
import { useToast } from '../../components/common/ToastProvider';
import partnerOrganizationsService, { type PartnerSuggestion } from '../../services/partnerOrganizations.service';

export default function PartnerOrganizationSuggestions() {
  const { success, error } = useToast();
  const [items, setItems] = useState<PartnerSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await partnerOrganizationsService.listPending());
    } catch {
      error('Could not load partner organisation suggestions.');
    } finally {
      setLoading(false);
    }
  }, [error]);

  useEffect(() => { void refresh(); }, [refresh]);

  const review = async (item: PartnerSuggestion, decision: 'approved' | 'rejected') => {
    setBusyId(item.id);
    try {
      await partnerOrganizationsService.review(item.id, decision);
      success(decision === 'approved' ? 'Partner added to the shared directory.' : 'Partner suggestion rejected.');
      setItems((current) => current.filter((candidate) => candidate.id !== item.id));
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      error(typeof detail === 'string' ? detail : detail?.message ?? 'Could not review this partner suggestion.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="mt-8 overflow-hidden rounded-[var(--radius-3)] border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-6 py-5">
        <h3 className="text-2xl font-light text-slate-900">
          Partner directory suggestions {!loading && `(${items.length})`}
        </h3>
        <p className="mt-1 text-sm text-slate-500">Approved entries appear in project delivery-partner suggestions, separate from registered organisations.</p>
      </div>
      {loading ? (
        <div className="px-6 py-8 text-sm text-slate-500">Loading…</div>
      ) : items.length === 0 ? (
        <div className="px-6 py-8 text-sm text-slate-500">No pending partner suggestions.</div>
      ) : (
        <ul className="divide-y divide-slate-100">
          {items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-4 px-6 py-4">
              <div>
                <div className="font-medium text-slate-800">{item.name}</div>
                <div className="text-xs text-slate-500">
                  {item.partner_type === 'DESIGNERS' ? 'Designer' : 'Construction'} · suggested {new Date(item.created_at).toLocaleDateString()}
                </div>
              </div>
              <div className="flex gap-2">
                <button type="button" disabled={busyId === item.id} onClick={() => void review(item, 'rejected')} className="rounded border border-slate-300 px-3 py-2 text-sm disabled:opacity-50">Reject</button>
                <button type="button" disabled={busyId === item.id} onClick={() => void review(item, 'approved')} className="rounded bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50">Approve</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
