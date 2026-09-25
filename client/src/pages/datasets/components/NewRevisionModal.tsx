import { useState } from 'react';
import type { DatasetRevision } from '../types';
"use no memo";

type ScopeType = 'DEFAULT' | 'ORG' | 'PROJECT';

/**
 * Creation modes per scope tier:
 *  DEFAULT → blank | template
    *    blank:    Create an empty draft dataset (e.g. for a brand-new reporting year).
    *    template: Clone an existing DEFAULT revision as a starting point (e.g. copy CY2026 → CY2027 with minimal changes required).
 *  ORG → blank | branch | version
    *    blank:   Create an empty org-scoped draft.
    *    branch:  Clone a published global revision into a new org-scoped draft (org starts with platform defaults, then customises).
    *    version: Clone an existing org revision to create the next version (e.g. copy the org's CY2026 dataset into a CY2027 draft).
 *  PROJECT → branch only
    *    branch:  Clone a published global or org revision into a project-scoped draft. Projects always start from an upstream source; standalone creation is not allowed.
 */
type Mode = 'blank' | 'template' | 'branch' | 'version';

const MODES_BY_SCOPE: Record<ScopeType, Mode[]> = {
  DEFAULT: ['template', 'blank'],
  ORG:     ['branch', 'version'],
  PROJECT: ['branch'],
};

function getModeLabel(m: Mode, scopeType: ScopeType): string {
  if (m === 'template') return 'Use as template';
  if (m === 'blank')    return 'Blank';
  if (m === 'branch')   return scopeType === 'ORG' ? 'Branch from Global' : 'Branch from Global / Org';
  return 'New version';
}

function getSubmitLabel(m: Mode): string {
  if (m === 'blank')    return 'Create';
  if (m === 'template') return 'Create from template';
  if (m === 'branch')   return 'Branch';
  return 'Create version';
}

interface Props {
  scopeType: ScopeType;
  revisions: DatasetRevision[];
  sourceRevisions: DatasetRevision[];
  onClose: () => void;
  onCreate: (name: string, notes: string, sourceId: string | null) => Promise<void>;
}

export default function NewRevisionModal({
  scopeType, revisions, sourceRevisions, onClose, onCreate,
}: Props) {
  const availableModes = MODES_BY_SCOPE[scopeType];
  const [mode, setMode]         = useState<Mode>(availableModes[0]);
  const [sourceId, setSourceId] = useState('');
  const [name, setName]         = useState('');
  const [notes, setNotes]       = useState('');
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState('');

  const ownBranchable    = revisions.filter(r => r.status !== 'archived');
  const sourceBranchable = sourceRevisions.filter(r => r.status !== 'archived');

  const activeRevisionList = mode === 'branch' ? sourceBranchable : ownBranchable;
  const needsSource        = mode !== 'blank';

  const handleModeChange = (m: Mode) => { setMode(m); setSourceId(''); setError(''); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) { setError('Name is required.'); return; }
    if (needsSource && !sourceId) {
      setError(
        mode === 'template' ? 'Select a dataset to use as a template.' :
        mode === 'version'  ? 'Select the existing version to base this on.' :
                              'Select a revision to branch from.',
      );
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onCreate(name.trim(), notes.trim(), needsSource ? sourceId : null);
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as { code?: string; response?: { data?: { detail?: unknown } } };
      if (axiosErr.code === 'ECONNABORTED' || axiosErr.code === 'ERR_NETWORK') {
        setError('Request timed out or the server is unreachable. Please try again.');
      } else {
        const detail = axiosErr?.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : 'Failed to create revision.');
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-neutral-90 px-6 py-4">
          <h2 className="text-base font-semibold text-text-dark">New dataset revision</h2>
          <button
            type="button" onClick={onClose}
            className="text-text-base cursor-pointer hover:text-text-dark text-lg leading-none"
          >×</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">

          {availableModes.length > 1 && (
            <div className="flex rounded border border-neutral-80 overflow-hidden text-sm w-fit">
              {availableModes.map(m => (
                <button
                  key={m} type="button"
                  onClick={() => handleModeChange(m)}
                  className={[
                    'px-4 py-1.5 cursor-pointer font-medium transition-colors',
                    mode === m
                      ? 'bg-primary text-white'
                      : 'bg-white text-text-base hover:bg-neutral-98',
                  ].join(' ')}
                >
                  {getModeLabel(m, scopeType)}
                </button>
              ))}
            </div>
          )}

          {mode === 'template' && (
            <p className="text-xs text-text-base">
              Copies all factor sets and their data rows as a starting point for the next
              dataset version (e.g. CY2026 → CY2027). Only minimal updates are then needed.
            </p>
          )}
          {mode === 'branch' && scopeType === 'ORG' && (
            <p className="text-xs text-text-base">
              Creates an org-scoped dataset pre-populated with a published global dataset's
              content. Your org can then override specific values.
            </p>
          )}
          {mode === 'branch' && scopeType === 'PROJECT' && (
            <p className="text-xs text-text-base">
              Project datasets are always branched from a published global or organisation
              dataset. All factor sets and emission-factor rows are copied into a new draft
              that you can customise for this project.
            </p>
          )}
          {mode === 'version' && (
            <p className="text-xs text-text-base">
              Creates a new org dataset version by copying an existing org revision. Ideal
              for rolling forward to the next reporting year with minimal rework.
            </p>
          )}

          {needsSource && (
            <div>
              <label className="block text-xs font-medium text-text-base mb-1">
                {mode === 'template' ? 'Template dataset' :
                 mode === 'version'  ? 'Base version' :
                 scopeType === 'ORG' ? 'Global dataset to branch from' :
                                       'Source dataset'}
              </label>
              {activeRevisionList.length === 0 ? (
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                  {mode === 'branch' && scopeType === 'PROJECT'
                    ? 'No published global or organisation datasets are available. Ask your administrator to publish one first.'
                    : mode === 'branch'
                    ? 'No published global datasets are available yet.'
                    : 'No existing revisions are available to use as a base.'}
                </p>
              ) : (
                <select
                  value={sourceId}
                  onChange={e => setSourceId(e.target.value)}
                  className="w-full rounded border border-neutral-80 px-3 py-2 text-sm focus:outline-none focus:border-primary"
                >
                  <option value="">Select revision…</option>
                  {activeRevisionList.map(r => (
                    <option key={r.id} value={r.id}>{r.name} ({r.status})</option>
                  ))}
                </select>
              )}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-text-base mb-1">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={
                mode === 'template' ? 'e.g. CY2027' :
                mode === 'branch' && scopeType === 'ORG' ? 'e.g. CY2026 (Org A)' :
                mode === 'branch'   ? 'e.g. CY2026 (Project X)' :
                mode === 'version'  ? 'e.g. CY2027 (Org A)' :
                'e.g. CY2026'
              }
              className="w-full rounded border border-neutral-80 px-3 py-2 text-sm focus:outline-none focus:border-primary"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-base mb-1">Notes</label>
            <textarea
              rows={2}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Optional description…"
              className="w-full rounded border border-neutral-80 px-3 py-2 text-sm focus:outline-none focus:border-primary resize-none"
            />
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button" onClick={onClose}
              className="rounded cursor-pointer border border-neutral-80 px-4 py-2 text-sm font-medium text-text-base hover:bg-neutral-98"
            >
              Cancel
            </button>
            <button
              type="submit" disabled={saving}
              className="rounded bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              {saving ? 'Creating…' : getSubmitLabel(mode)}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
