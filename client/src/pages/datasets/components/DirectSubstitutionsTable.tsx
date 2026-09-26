import { useState } from 'react';
import http from '@/http';
import type { DirectSubstitutionRow, NamedOption } from '../types';
import { TH, TD } from './TablePrimitives';

interface Props {
  rows: DirectSubstitutionRow[];
  canEdit: boolean;
  revisionId: string;
  jurisdictions: NamedOption[];
  onSaved: () => void;
}

type Draft = {
  jurisdiction_id: string;
  user_emissions_source: string;
  user_unit: string;
  bau_equivalent_emission_source: string;
  bau_equivalent_unit: string;
  bau_quantity_per_user_unit: string;
};

const emptyDraft = (jurisdiction_id = ''): Draft => ({
  jurisdiction_id,
  user_emissions_source: '',
  user_unit: '',
  bau_equivalent_emission_source: '',
  bau_equivalent_unit: '',
  bau_quantity_per_user_unit: '',
});

function toDraft(row: DirectSubstitutionRow): Draft {
  return {
    jurisdiction_id: row.jurisdiction_id,
    user_emissions_source: row.user_emissions_source,
    user_unit: row.user_unit,
    bau_equivalent_emission_source: row.bau_equivalent_emission_source,
    bau_equivalent_unit: row.bau_equivalent_unit,
    bau_quantity_per_user_unit: String(row.bau_quantity_per_user_unit),
  };
}

function formatQty(v: string | number): string {
  if (v === '' || v == null) return '—';
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return Number.isFinite(n) ? String(n) : String(v);
}

export default function DirectSubstitutionsTable({ rows, canEdit, revisionId, jurisdictions, onSaved }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const startEdit = (row: DirectSubstitutionRow) => {
    setError('');
    setAdding(false);
    setEditingId(row.id);
    setDraft(toDraft(row));
  };
  const cancel = () => { setEditingId(null); setAdding(false); setError(''); };
  const setField = (key: keyof Draft, value: string) => setDraft(current => ({ ...current, [key]: value }));

  const save = async () => {
    if (!draft.jurisdiction_id || !draft.user_emissions_source.trim() || !draft.user_unit.trim() ||
        !draft.bau_equivalent_emission_source.trim() || !draft.bau_equivalent_unit.trim() ||
        draft.bau_quantity_per_user_unit.trim() === '' || !Number.isFinite(Number(draft.bau_quantity_per_user_unit))) {
      setError('Complete all fields with a valid quantity.');
      return;
    }
    setSaving(true);
    setError('');
    const payload = { ...draft, bau_quantity_per_user_unit: Number(draft.bau_quantity_per_user_unit) };
    try {
      if (adding) {
        await http.post('/api/direct-substitutions/upsert', { ...payload, dataset_revision_id: revisionId });
      } else if (editingId) {
        await http.patch(`/api/direct-substitutions/${editingId}`, payload);
      }
      cancel();
      onSaved();
    } catch {
      setError('Could not save this direct substitution. Check your access and try again.');
    } finally {
      setSaving(false);
    }
  };

  const input = (key: keyof Draft, placeholder: string, type = 'text') => (
    <input type={type} step={type === 'number' ? 'any' : undefined} value={draft[key]}
      onChange={e => setField(key, e.target.value)} placeholder={placeholder}
      className="w-full min-w-24 rounded border border-primary px-1.5 py-1 text-xs" />
  );
  const jurisdictionSelect = (
    <select value={draft.jurisdiction_id} onChange={e => setField('jurisdiction_id', e.target.value)}
      className="w-full min-w-28 rounded border border-primary px-1 py-1 text-xs">
      <option value="">Select jurisdiction</option>
      {jurisdictions.map(option => <option key={option.id} value={option.id}>{option.name}</option>)}
    </select>
  );
  const editorRow = (key: string) => (
    <tr key={key} className="bg-blue-50">
      <TD>{input('user_emissions_source', 'Source')}</TD>
      <TD>{input('user_unit', 'Unit')}</TD>
      <TD>{input('bau_equivalent_emission_source', 'BAU source')}</TD>
      <TD>{input('bau_equivalent_unit', 'BAU unit')}</TD>
      <TD right>{input('bau_quantity_per_user_unit', 'Quantity', 'number')}</TD>
      <TD>{jurisdictionSelect}</TD>
      <TD><div className="flex gap-2"><button type="button" disabled={saving} onClick={() => void save()} className="text-primary font-semibold disabled:opacity-50">{saving ? 'Saving…' : 'Save'}</button><button type="button" onClick={cancel}>Cancel</button></div>{error && <p className="mt-1 text-red-600">{error}</p>}</TD>
    </tr>
  );

  return (
    <div className="h-full overflow-auto">
      {canEdit && <div className="sticky top-0 z-10 flex justify-end bg-white p-2"><button type="button" disabled={adding || !!editingId} onClick={() => { setDraft(emptyDraft(jurisdictions[0]?.id)); setAdding(true); setError(''); }} className="rounded bg-primary px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">Add direct substitution</button></div>}
      <table className="w-full border-collapse text-xs">
        <thead className="sticky top-10 z-10 bg-neutral-90"><tr><TH>User emissions source</TH><TH>User unit</TH><TH>BAU equivalent emission source</TH><TH>BAU equivalent unit</TH><TH right>BAU quantity per user unit</TH><TH>Jurisdiction</TH>{canEdit && <TH>Actions</TH>}</tr></thead>
        <tbody>
          {adding && editorRow('new')}
          {rows.map(row => editingId === row.id ? editorRow(row.id) : (
            <tr key={row.id} className="even:bg-neutral-98 hover:bg-blue-50">
              <TD muted>{row.user_emissions_source || '—'}</TD><TD>{row.user_unit || '—'}</TD>
              <TD muted>{row.bau_equivalent_emission_source || '—'}</TD><TD>{row.bau_equivalent_unit || '—'}</TD>
              <TD right>{formatQty(row.bau_quantity_per_user_unit)}</TD><TD>{row.jurisdiction_name || '—'}</TD>
              {canEdit && <TD><button type="button" disabled={adding || !!editingId} onClick={() => startEdit(row)} className="text-primary font-medium disabled:opacity-50">
                <span className="material-symbols-rounded text-[14px] leading-none">edit</span>
              </button></TD>}
            </tr>
          ))}
          {!rows.length && !adding && <tr><td colSpan={canEdit ? 7 : 6} className="p-6 text-center text-text-base">No direct substitution factors match the current filters</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
