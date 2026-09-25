/**
 * pages/auditLog/AuditLogPage.tsx
 *
 * Project-scoped audit log viewer.
 * Only visible to ORG_ADMIN and SUPER_ADMIN roles.
 */

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchProjectAuditLogs } from '@/services/AuditLog.service';
import ProjectsService from '@/services/Projects.service';
import { useUser } from '@/context/UserContext';
import { useProjectHeader } from '@/context/ProjectHeaderContext';
import { extractApiError } from '@/utils/utils';
import type { AuditLogRow } from '@/pages/datasets/types';

export const ACTION_BADGE: Record<string, string> = {
  CREATE: 'bg-green-100 text-green-700',
  UPDATE: 'bg-blue-100 text-blue-700',
  DELETE: 'bg-red-100 text-red-700',
  CLOSE: 'bg-yellow-100 text-yellow-700',
  REOPEN: 'bg-purple-100 text-purple-700',
};

export const STAGE_LABELS: Record<string, string> = {
  BUSINESS_CASE: 'Business Case',
  DESIGN: 'Design',
  CONSTRUCTION: 'Construction',
  RECURRING: 'Recurring',
};

export const ENTITY_TYPE_LABELS: Record<string, string> = {
  project: 'Project',
  activity_data: 'Activity Data',
  emission_entry: 'Emission Entry',
  project_mitigation: 'Mitigation',
};

export const UI_TABLE_KEY_LABELS: Record<string, string> = {
  asset: 'Asset',
  component: 'Component',
  componentRepl: 'Component Replacement',
  refurbishment: 'Refurbishment',
  replDetailed: 'Replacement (Detailed)',
  opEnergy: 'Operational Energy',
  opEnergyDetailed: 'Operational Energy (Detailed)',
  opEnergyElectricity: 'Op. Energy Electricity',
  electricity: 'Electricity',
  constructionG2: 'Construction (G2)',
  constructionG3: 'Construction (G3)',
  bcDetailedLevel: 'Business Case (Detailed)',
  useB1G2: 'Use Stage (G2)',
  useB1G3: 'Use Stage (G3)',
  concreteRegSimplified: 'Concrete Register (Simplified)',
  concreteRegDetailed: 'Concrete Register (Detailed)',
  recurringG3: 'Recurring (G3)',
};

// Maps ui_table_key to a human-readable lifecycle substage category
export const UI_TABLE_KEY_TO_SUBSTAGE: Record<string, string> = {
  constructionG2: 'Construction',
  constructionG3: 'Construction',
  useB1G2: 'Use Stage',
  useB1G3: 'Use Stage',
  componentRepl: 'Replacement',
  replDetailed: 'Replacement',
  refurbishment: 'Refurbishment',
  opEnergy: 'Operational Energy',
  opEnergyDetailed: 'Operational Energy',
  opEnergyElectricity: 'Operational Energy',
  electricity: 'Operational Energy',
  concreteRegSimplified: 'Concrete Register',
  concreteRegDetailed: 'Concrete Register',
  recurringG3: 'Recurring',
};

export function ActionBadge({ action }: { action: string }) {
  const cls = ACTION_BADGE[action.toUpperCase()] ?? 'bg-neutral-200 text-gray-700';
  return (
    <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ${cls}`}>
      {action}
    </span>
  );
}

export type AuditMeta = {
  stage?: string;
  ui_table_key?: string;
  option_label?: string;
  period_label?: string;
  /** Legacy project-level field diffs */
  field_diffs?: Array<{ field: string; old_value: string | null; new_value: string | null }>;
  /** activity_data CREATE: full snapshot of new row */
  new_values?: Record<string, unknown>;
  old_values?: Record<string, unknown>;
  /** activity_data UPDATE: changed fields {field: {before, after}} */
  changes?: Record<string, { before: unknown; after: unknown }>;
  [key: string]: unknown;
};

export const AUDIT_FIELD_LABELS: Record<string, string> = {
  quantity: 'Quantity',
  unit_id: 'Unit ID',
  lifecycle_module_code: 'Lifecycle Module',
  dataset_revision_id: 'Dataset Revision',
  metric_natural_key: 'Metric',
};

/** Labels for extra_fields sub-keys (used after stripping the 'ef:' prefix) */
export const EF_FIELD_LABELS: Record<string, string> = {
  year: 'Year',
  unit_display: 'Unit',
  unit_code: 'Unit',
  emission_source: 'Source',
  emissions_source: 'Source',
  emissions_category: 'Category',
  emissions_subcategory: 'Subcategory',
  emissions_category_id: 'Category',
  emissions_source_name: 'Source',
  emissions_subcategory_id: 'Subcategory',
  notes: 'Notes',
  notes_author: 'Author',
  notes_date: 'Date',
  quantity_mwh: 'Quantity (MWh)',
  quantity_tonne: 'Quantity (t)',
  quantity_kwh: 'Quantity (kWh)',
  quantity_ml: 'Quantity (ML)',
  quantity_l: 'Quantity (L)',
  quantity_km: 'Quantity (km)',
  quantity_m2: 'Quantity (m²)',
  quantity_m3: 'Quantity (m³)',
};

export const _EF_EMISSION_KEYS = new Set([
  'emission_source', 'emissions_source', 'emissions_source_name',
  'emissions_category', 'emissions_category_id',
  'emissions_subcategory', 'emissions_subcategory_id',
]);
export const _EF_NOTE_KEYS = new Set(['notes', 'notes_author', 'notes_date']);

export function _fmt(value: unknown): string {
  if (value == null) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function _fmtDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function Section({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  if (!rows.length) return null;
  return (
    <div>
      <div className="font-semibold text-[9px] uppercase tracking-wide text-gray-400 mb-0.5">{title}</div>
      {rows.map(([label, value]) => (
        <div key={label} className="pl-2 leading-snug">
          <span className="text-gray-500">{label}:</span>{' '}
          <span className="text-gray-700">{value}</span>
        </div>
      ))}
    </div>
  );
}

export function ActivityDataNew({ vals }: { vals: Record<string, unknown> }) {
  // Separate top-level snapshot keys from flattened extra_fields (ef:* prefix)
  const efVals: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(vals)) {
    if (k.startsWith('ef:')) efVals[k.slice(3)] = v;
  }

  const qty = vals.quantity;
  const unitDisplay = efVals.unit_display ?? efVals.unit_code;

  const entryRows: Array<[string, string]> = [];
  if (qty != null) entryRows.push(['Quantity', unitDisplay ? `${qty} ${unitDisplay}` : String(qty)]);
  if (vals.lifecycle_module_code) entryRows.push(['Lifecycle Module', String(vals.lifecycle_module_code)]);
  if (efVals.year != null) entryRows.push(['Year', String(efVals.year)]);
  // Add any quantity_* fields (table-specific unit variants)
  for (const [k, v] of Object.entries(efVals)) {
    if (k.startsWith('quantity_') && v != null) {
      entryRows.push([EF_FIELD_LABELS[k] ?? k, String(v)]);
    }
  }

  const emRows: Array<[string, string]> = [];
  for (const k of _EF_EMISSION_KEYS) {
    if (efVals[k] != null) emRows.push([EF_FIELD_LABELS[k] ?? k, String(efVals[k])]);
  }

  const noteRows: Array<[string, string]> = [];
  if (efVals.notes) noteRows.push(['Text', String(efVals.notes)]);
  if (efVals.notes_author) noteRows.push(['Author', String(efVals.notes_author)]);
  if (efVals.notes_date) noteRows.push(['Date', _fmtDate(String(efVals.notes_date))]);

  // Any remaining ef: fields not assigned to a section above
  const handledEfKeys = new Set(['year', 'unit_display', 'unit_code', ..._EF_EMISSION_KEYS, ..._EF_NOTE_KEYS]);
  const otherRows: Array<[string, string]> = Object.entries(efVals)
    .filter(([k]) => !handledEfKeys.has(k) && !k.startsWith('quantity_'))
    .map(([k, v]) => [EF_FIELD_LABELS[k] ?? k, _fmt(v)]);

  const hasSections = entryRows.length || emRows.length || noteRows.length || otherRows.length;
  if (!hasSections) return <span className="text-gray-400">—</span>;

  return (
    <div className="space-y-1.5 text-[10px]">
      <Section title="Audit Entry" rows={entryRows} />
      <Section title="Emissions" rows={emRows} />
      <Section title="Notes" rows={noteRows} />
      {otherRows.length > 0 && <Section title="Other" rows={otherRows} />}
    </div>
  );
}

const _CHANGES_SKIP_KEYS = new Set([
  'extra_fields',          // raw JSON blob — newer records expand this via ef:* keys
  '_fromBoundary', 'fromBoundary',
  'emissions_tco2e', 'market_based_tco2e',
  'location_based_tco2e', 'total_emissions_tco2e', 'carbon_credits',
  'unit_display', 'unit_code', 'unit',
  'emissions_source_name',
]);

export function ActivityDataChanges({ changes }: { changes: Record<string, { before: unknown; after: unknown }> }) {
  const fmtVal = (v: unknown, k: string) =>
    k === 'notes_date' && v != null ? _fmtDate(String(v)) : _fmt(v);
  const entries = Object.entries(changes).filter(([field]) => {
    const key = field.startsWith('ef:') ? field.slice(3) : field;
    if (key.endsWith('_id')) return false;
    if (_CHANGES_SKIP_KEYS.has(key)) return false;
    return true;
  });
  if (!entries.length) return <span className="text-gray-400">—</span>;
  return (
    <ul className="space-y-0.5 text-[10px]">
      {entries.map(([field, { before, after }]) => {
        const key = field.startsWith('ef:') ? field.slice(3) : field;
        const label = AUDIT_FIELD_LABELS[key] ?? EF_FIELD_LABELS[key] ?? key;
        return (
          <li key={field}>
            <span className="font-medium text-gray-600">{label}:</span>{' '}
            {before != null
              ? <span className="text-red-400 line-through">{fmtVal(before, key)}</span>
              : <span className="text-gray-400">—</span>}
            {' → '}
            {after != null
              ? <span className="text-green-600">{fmtVal(after, key)}</span>
              : <span className="text-gray-400">—</span>}
          </li>
        );
      })}
    </ul>
  );
}

export function ExtraFieldsList({
  vals,
  changes,
}: {
  vals: Record<string, unknown>;
  changes?: Record<string, { before: unknown; after: unknown }>;
}) {
  const fmtVal = (v: unknown, key: string): string =>
    key === 'notes_date' && v != null ? _fmtDate(String(v)) : _fmt(v);

  const EXCLUDE_EF = new Set(['unit_display', 'unit_code', 'unit', 'emissions_source_name', 'fromBoundary', '_fromBoundary']);
  const entries = Object.entries(vals).filter(([field]) => {
    if (field === 'quantity') return true;
    if (!field.startsWith('ef:')) return false;
    const key = field.slice(3);
    if (key.endsWith('_id')) return false;
    if (EXCLUDE_EF.has(key)) return false;
    return true;
  });

  if (!entries.length) return <span className="text-gray-400">—</span>;

  return (
    <ul className="space-y-0.5 text-[10px]">
      {entries.map(([field, val]) => {
        const key = field.startsWith('ef:') ? field.slice(3) : field;
        const label = AUDIT_FIELD_LABELS[key] ?? EF_FIELD_LABELS[key] ?? key;
        const change = changes?.[field];
        if (change) {
          return (
            <li key={field}>
              <span className="font-medium text-gray-600">{label}:</span>{' '}
              {change.before != null
                ? <span className="text-red-400 line-through">{fmtVal(change.before, key)}</span>
                : <span className="text-gray-400">—</span>}
              {' → '}
              {change.after != null
                ? <span className="text-green-600">{fmtVal(change.after, key)}</span>
                : <span className="text-gray-400">—</span>}
            </li>
          );
        }
        return (
          <li key={field}>
            <span className="font-medium text-gray-600">{label}:</span>{' '}
            <span className="text-gray-700">{fmtVal(val, key)}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function StageCell({ row }: { row: AuditLogRow }) {
  const meta = (row.event_metadata ?? {}) as AuditMeta;
  if (!meta.stage) return <span className="text-gray-400">—</span>;
  const details: string[] = [];
  if (meta.option_label) details.push(meta.option_label);
  if (meta.period_label) details.push(meta.period_label);
  return (
    <div>
      <div className="font-medium text-gray-700">{STAGE_LABELS[meta.stage] ?? meta.stage}</div>
      {details.length > 0 && (
        <div className="text-[10px] text-gray-400 mt-0.5 leading-snug">
          {details.map((d) => <div key={d}>{d}</div>)}
        </div>
      )}
    </div>
  );
}

export function SubstageCell({ row }: { row: AuditLogRow }) {
  const meta = (row.event_metadata ?? {}) as AuditMeta;
  const substage = meta.ui_table_key ? UI_TABLE_KEY_TO_SUBSTAGE[meta.ui_table_key] : undefined;
  if (!substage) return <span className="text-gray-400">—</span>;
  return <span className="text-gray-600">{substage}</span>;
}

export function TableCell({ row }: { row: AuditLogRow }) {
  const meta = (row.event_metadata ?? {}) as AuditMeta;
  // Prefer ui_table_key from metadata, fall back to entity_name (also a ui_table_key for activity_data),
  // then entity_type label — ensures the column is never blank.
  const key = meta.ui_table_key ?? row.entity_name ?? '';
  const label =
    UI_TABLE_KEY_LABELS[key] ??
    ENTITY_TYPE_LABELS[row.entity_type] ??
    row.entity_name ??
    row.entity_type;
  return <span className="text-gray-700">{label}</span>;
}

export default function AuditLogPage() {
  const { projectId } = useParams<{ projectId: string }>();
  // const navigate = useNavigate();
  const { roles } = useUser();
  const { setProjectHeader, clearProjectHeader } = useProjectHeader();

  const isAllowed = roles.includes('ORG_ADMIN') || roles.includes('SUPER_ADMIN');

  const [projectName, setProjectName] = useState<string>('');
  const [rows, setRows] = useState<AuditLogRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Server-side filters
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  // Client-side filters
  const [userFilter, setUserFilter] = useState('');
  const [tableFilter, setTableFilter] = useState('');
  const [stageFilter, setStageFilter] = useState('');

  // Sort direction for Timestamp column
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  // Fetch project name for breadcrumb
  useEffect(() => {
    if (!projectId) return;
    ProjectsService.fetchProjectDetails(projectId)
      .then((proj) => {
        const name = proj.project_name ?? '';
        setProjectName(name);
        setProjectHeader(name, false, projectId);
      })
      .catch((err) => console.debug('[AuditLogPage] Non-critical project name fetch failed:', err));
    return () => clearProjectHeader();
  }, [projectId]);

  useEffect(() => {
    if (!projectId || !isAllowed) return;
    setLoading(true);
    setError(null);
    fetchProjectAuditLogs(projectId, {
      action: actionFilter || undefined,
      from_date: fromDate || undefined,
      to_date: toDate || undefined,
      limit: 200,
    })
      .then(setRows)
      .catch((err) => setError(extractApiError(err, 'Failed to load audit logs.')))
      .finally(() => setLoading(false));
  }, [projectId, isAllowed, actionFilter, fromDate, toDate]);

  const displayRows = useMemo(() => {
    let out = rows;
    if (userFilter.trim()) {
      const q = userFilter.trim().toLowerCase();
      out = out.filter(
        (r) =>
          (r.performed_by_email ?? '').toLowerCase().includes(q) ||
          (r.performed_by ?? '').toLowerCase().includes(q),
      );
    }
    if (tableFilter) {
      out = out.filter((r) => {
        const m = (r.event_metadata ?? {}) as AuditMeta;
        return m.ui_table_key === tableFilter;
      });
    }
    if (stageFilter) {
      out = out.filter((r) => {
        const m = (r.event_metadata ?? {}) as AuditMeta;
        return m.stage === stageFilter;
      });
    }
    if (sortDir === 'asc') {
      out = [...out].sort(
        (a, b) =>
          new Date(a.performed_at ?? 0).getTime() -
          new Date(b.performed_at ?? 0).getTime(),
      );
    }
    return out;
  }, [rows, userFilter, tableFilter, stageFilter, sortDir]);

  const hasClientFilters = userFilter.trim() || tableFilter || stageFilter;
  const hasServerFilters = actionFilter || fromDate || toDate;

  if (!isAllowed) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-400">
        You do not have permission to view audit logs.
      </div>
    );
  }

  return (
    <div className="min-h-full bg-bg-content">
      {/* Header bar — consistent with ProjectDetail */}
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
          {projectName ? `${projectName} — Audit Log` : 'Project Audit Log'}
        </div>
      </div>

      <div className="mx-auto w-[90%] px-4 py-6 space-y-6">
      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-sm p-4 space-y-3">
        <div className="flex flex-wrap gap-4 items-end">
          {/* User */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">User</label>
            <input
              type="text"
              placeholder="Search user…"
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm bg-white text-text-base w-44 focus:outline-none focus:ring-1"
            />
          </div>
          {/* Action */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Action</label>
            <div className="relative">
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="appearance-none border border-gray-300 rounded px-3 py-1.5 pr-8 text-sm bg-white text-text-base focus:outline-none focus:ring-1"
              >
                <option value="">All actions</option>
                <option value="CREATE">Create</option>
                <option value="UPDATE">Update</option>
                <option value="DELETE">Delete</option>
                <option value="CLOSE">Close</option>
                <option value="REOPEN">Reopen</option>
              </select>
              <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-600">
                <span className="material-symbols-rounded text-[18px] leading-none">expand_more</span>
              </span>
            </div>
          </div>
          {/* Table */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Table</label>
            <div className="relative">
              <select
                value={tableFilter}
                onChange={(e) => setTableFilter(e.target.value)}
                className="appearance-none border border-gray-300 rounded px-3 py-1.5 pr-8 text-sm bg-white text-text-base focus:outline-none focus:ring-1"
              >
                <option value="">All tables</option>
                {Object.entries(UI_TABLE_KEY_LABELS).map(([k, label]) => (
                  <option key={k} value={k}>{label}</option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-600">
                <span className="material-symbols-rounded text-[18px] leading-none">expand_more</span>
              </span>
            </div>
          </div>
          {/* Stage */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Stage</label>
            <div className="relative">
              <select
                value={stageFilter}
                onChange={(e) => setStageFilter(e.target.value)}
                className="appearance-none border border-gray-300 rounded px-3 py-1.5 pr-8 text-sm bg-white text-text-base focus:outline-none focus:ring-1"
              >
                <option value="">All stages</option>
                {Object.entries(STAGE_LABELS).map(([k, label]) => (
                  <option key={k} value={k}>{label}</option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-600">
                <span className="material-symbols-rounded text-[18px] leading-none">expand_more</span>
              </span>
            </div>
          </div>
          {/* Date range */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">From date</label>
            <input
              type="datetime-local"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm bg-white text-text-base focus:outline-none focus:ring-1"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">To date</label>
            <input
              type="datetime-local"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm bg-white text-text-base focus:outline-none focus:ring-1"
            />
          </div>
          {(hasClientFilters || hasServerFilters) && (
            <button
              type="button"
              onClick={() => {
                setUserFilter('');
                setTableFilter('');
                setStageFilter('');
                setActionFilter('');
                setFromDate('');
                setToDate('');
              }}
              className="text-xs text-gray-500 hover:text-gray-800 self-end pb-2 cursor-pointer"
            >
              Clear all
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-sm overflow-hidden">
        {loading ? (
          <div className="flex h-40 items-center justify-center text-sm text-gray-400">Loading…</div>
        ) : error ? (
          <div className="flex h-40 items-center justify-center text-sm text-red-500">{error}</div>
        ) : rows.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-gray-400 italic">
            No audit log entries found.
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
                  <th className="px-3 py-2 text-left font-medium text-gray-500">
                    <button
                      type="button"
                      onClick={() => setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))}
                      className="flex items-center gap-1 hover:text-gray-800 cursor-pointer"
                    >
                      Timestamp
                      <span className="material-symbols-rounded text-[8px] leading-none">
                        {sortDir === 'desc' ? 'arrow_downward' : 'arrow_upward'}
                      </span>
                    </button>
                  </th>
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
              {displayRows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-sm text-gray-400 italic">
                    No entries match the current filters.
                  </td>
                </tr>
              ) : displayRows.map((r) => {
                const meta = (r.event_metadata ?? {}) as AuditMeta;
                const fieldDiffs = meta.field_diffs ?? [];
                return (
                  <tr key={r.id} className="even:bg-gray-50 hover:bg-blue-50 transition-colors">
                    <td className="px-3 py-2 text-gray-500">
                      {r.performed_at ? new Date(r.performed_at).toLocaleString('en-AU') : '—'}
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
                      {(meta.new_values || meta.old_values) ? (
                        <ExtraFieldsList
                          vals={(meta.new_values ?? meta.old_values) as Record<string, unknown>}
                          changes={meta.changes as Record<string, { before: unknown; after: unknown }> | undefined}
                        />
                      ) : meta.changes ? (
                        <ActivityDataChanges changes={meta.changes as Record<string, { before: unknown; after: unknown }>} />
                      ) : fieldDiffs.length > 0 ? (
                        <ul className="space-y-1">
                          {fieldDiffs.map((d, i) => (
                            <li key={`${d.field}-${i}`} className="text-[10px]">
                              <span className="font-medium text-gray-600">{d.field}:</span>{' '}
                              <span className="text-red-500 line-through">{d.old_value ?? 'null'}</span>
                              {' → '}
                              <span className="text-green-600">{d.new_value ?? 'null'}</span>
                            </li>
                          ))}
                        </ul>
                      ) : r.field_name ? (
                        <span className="text-[10px]">
                          <span className="font-medium text-gray-600">{r.field_name}:</span>{' '}
                          <span className="text-red-500 line-through">{r.old_value ?? 'null'}</span>
                          {' → '}
                          <span className="text-green-600">{r.new_value ?? 'null'}</span>
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400">
        Showing {displayRows.length}{displayRows.length !== rows.length ? ` of ${rows.length}` : ''} entries.
      </p>
      </div>
    </div>
  );
}
