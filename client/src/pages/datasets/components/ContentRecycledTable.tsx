import type {
  ContentRecycledRow,
  ContentRecycledEditCtx,
  ContentRecycledEditableField,
} from '../types';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

function pctToDisplay(v: string | null | undefined): string {
  if (v == null || v === '') return '—';
  const n = parseFloat(v);
  if (Number.isNaN(n)) return '—';
  const scaled = n * 100;
  return Number.isInteger(scaled) ? String(scaled) : scaled.toFixed(2).replace(/\.?0+$/, '');
}

function pctToEditDraft(v: string | null | undefined): string {
  if (v == null || v === '') return '';
  const n = parseFloat(v);
  if (Number.isNaN(n)) return '';
  const scaled = n * 100;
  return Number.isInteger(scaled) ? String(scaled) : String(scaled);
}

interface Props {
  rows: ContentRecycledRow[];
  editCtx?: ContentRecycledEditCtx;
}

export default function ContentRecycledTable({ rows, editCtx }: Props) {
  const ec = editCtx;
  const isSA = !!ec;

  const renderEditableCell = (
    row: ContentRecycledRow,
    field: ContentRecycledEditableField,
    display: string,
    alignRight = false,
  ) => {
    const cellKey = `${row.id}::${field}`;
    const isEditing = ec?.editCellKey === cellKey;
    const isEmpty = display === '—';

    if (isEditing && ec) {
      return (
        <TD right={alignRight}>
          <div
            className={`flex items-center gap-1 ${alignRight ? 'justify-end' : ''}`}
            tabIndex={-1}
            onBlur={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveCell();
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                e.stopPropagation();
                ec.onCancelCell();
              } else if (e.key === 'Enter') {
                e.stopPropagation();
                ec.onSaveCell();
              }
            }}
          >
            <InlineInput
              type={field === 'notes' ? 'text' : 'number'}
              value={ec.cellDraft}
              onChange={v => ec.onCellChange(v)}
              placeholder={field === 'notes' ? 'Notes' : 'Value'}
            />
            <SaveCancelButtons
              onSave={ec.onSaveCell}
              onCancel={ec.onCancelCell}
              saving={ec.saving}
              error={ec.saveError}
            />
          </div>
        </TD>
      );
    }

    const initial =
      field === 'notes'
        ? (row.notes ?? '')
        : pctToEditDraft(field === 'recycled_content_pct' ? row.recycled_content_pct : row.reused_content_pct);

    return (
      <TD right={alignRight} muted={isEmpty}>
        <button
          type="button"
          disabled={!isSA || !!ec?.adding}
          onClick={
            isSA && !ec?.adding
              ? () => ec!.onEditCell(row.id, field, initial)
              : undefined
          }
          className={`w-full ${alignRight ? 'text-right tabular-nums' : 'text-left'} ${
            isSA && !ec?.adding ? 'cursor-text hover:text-primary' : 'cursor-default'
          }`}
        >
          {display}
        </button>
      </TD>
    );
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH>Emission Source</TH>
          <TH>Category</TH>
          <TH right>Recycled Content (%)</TH>
          <TH right>Reused Content (%)</TH>
          <TH>Notes/Comments</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {ec?.adding && (
          <tr className="bg-blue-50">
            <TD>
              <div className="flex flex-col gap-1">
                <InlineSelect
                  value={ec.addDraft.jurisdiction_id ?? ''}
                  options={ec.jurOpts}
                  onChange={v => ec.onAddField('jurisdiction_id', v)}
                  placeholder="— jurisdiction —"
                />
                <InlineInput
                  value={ec.addDraft.emissions_source ?? ''}
                  onChange={v => ec.onAddField('emissions_source', v)}
                  placeholder="Emission source"
                />
              </div>
            </TD>
            <TD>
              <InlineSelect
                value={ec.addDraft.emissions_sub_category_id ?? ''}
                options={ec.catOpts}
                onChange={v => ec.onAddField('emissions_sub_category_id', v)}
                placeholder="— category —"
              />
            </TD>
            <TD right>
              <InlineInput
                type="number"
                value={ec.addDraft.recycled_content_pct ?? ''}
                onChange={v => ec.onAddField('recycled_content_pct', v)}
                placeholder="Value"
              />
            </TD>
            <TD right>
              <InlineInput
                type="number"
                value={ec.addDraft.reused_content_pct ?? ''}
                onChange={v => ec.onAddField('reused_content_pct', v)}
                placeholder="Value"
              />
            </TD>
            <TD>
              <InlineInput
                value={ec.addDraft.notes ?? ''}
                onChange={v => ec.onAddField('notes', v)}
                placeholder="Notes"
              />
            </TD>
            <TD>
              <SaveCancelButtons onSave={ec.onSaveAdd} onCancel={ec.onCancelAdd} saving={ec.saving} error={ec.saveError} />
            </TD>
          </tr>
        )}
        {rows.map((r, i) => (
          <tr key={r.id ?? i} className="even:bg-neutral-98 hover:bg-blue-50">
            <TD>{r.emissions_source ?? '—'}</TD>
            <TD muted={!r.category_name}>{r.category_name ?? '—'}</TD>
            {renderEditableCell(r, 'recycled_content_pct', pctToDisplay(r.recycled_content_pct), true)}
            {renderEditableCell(r, 'reused_content_pct', pctToDisplay(r.reused_content_pct), true)}
            {renderEditableCell(r, 'notes', r.notes?.trim() ? r.notes : '—')}
            {isSA && (
              <TD>
                {!ec?.editCellKey && !ec?.adding && ec?.onDelete && (
                  <button
                    type="button"
                    onClick={() => ec.onDelete!(r.id)}
                    title="Delete row"
                    className="rounded p-0.5 cursor-pointer text-red-400 hover:text-red-600 hover:bg-red-50"
                  >
                    <span className="material-symbols-rounded text-[14px] leading-none">delete</span>
                  </button>
                )}
              </TD>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
