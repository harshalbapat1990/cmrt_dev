import type { MaintenanceReplacementRow, MaintenanceReplacementEditCtx } from '../types';
import { TH, TD, InlineInput, SaveCancelButtons } from './TablePrimitives';

interface Props {
  rows: MaintenanceReplacementRow[];
  editCtx?: MaintenanceReplacementEditCtx;
}

export default function MaintenanceReplacementTable({ rows, editCtx }: Props) {
  const ec = editCtx;

  return (
    <div className="overflow-x-auto overflow-y-auto h-full">
      <table className="border-collapse text-xs w-full">
        <thead className="sticky top-0 z-10 bg-neutral-90">
          <tr>
            <TH>Activity Type</TH>
            <TH>Item</TH>
            <TH>Unit</TH>
            <TH right normalCase>Emissions Intensity (tCO₂e/UoM)</TH>
            <TH right normalCase>Default Frequency (years)</TH>
            <TH normalCase>Source / Comments</TH>
            {ec && <TH>Actions</TH>}
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const isEditing = ec?.editingId === r.id;
            return (
              <tr
                key={r.id}
                className={`${isEditing ? 'bg-amber-50' : 'even:bg-neutral-98 hover:bg-primary/5'} ${ec && !isEditing ? 'cursor-pointer' : ''}`}
                onDoubleClick={ec && !isEditing ? () =>
                  ec.onStartEdit(r.id, {
                    emissions_intensity:
                      r.emissions_intensity_tco2e != null
                        ? String(r.emissions_intensity_tco2e)
                        : '',
                    default_frequency:
                      r.default_frequency_years != null
                        ? String(r.default_frequency_years)
                        : '',
                    source_note: r.source_note ?? '',
                  }) : undefined}
                tabIndex={isEditing ? -1 : undefined}
                onBlur={isEditing && ec ? (e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) ec.onSaveEdit(); } : undefined}
                onKeyDown={isEditing && ec ? (e) => { if (e.key === 'Escape') { e.stopPropagation(); ec.onCancelEdit(); } else if (e.key === 'Enter') { e.stopPropagation(); ec.onSaveEdit(); } } : undefined}
              >
                <TD>{r.activity_type}</TD>
                <TD>{r.item}</TD>
                <TD>{r.unit ? (r.unit.label ?? r.unit.code) : '—'}</TD>
                {isEditing && ec ? (
                  <>
                    <td className="px-2 py-1.5 border-r border-b border-neutral-90 min-w-[120px]">
                      <InlineInput
                        type="number"
                        value={ec.editDraft.emissions_intensity ?? ''}
                        onChange={v => ec.onEditField('emissions_intensity', v)}
                        placeholder="tCO₂e/UoM"
                      />
                    </td>
                    <td className="px-2 py-1.5 border-r border-b border-neutral-90 min-w-[80px]">
                      <InlineInput
                        type="number"
                        value={ec.editDraft.default_frequency ?? ''}
                        onChange={v => ec.onEditField('default_frequency', v)}
                        placeholder="years"
                      />
                    </td>
                    <td className="px-2 py-1.5 border-r border-b border-neutral-90 min-w-[220px]">
                      <InlineInput
                        value={ec.editDraft.source_note ?? ''}
                        onChange={v => ec.onEditField('source_note', v)}
                        placeholder="source / comments"
                      />
                    </td>
                    <td className="px-3 py-1.5 border-b border-neutral-90">
                      <SaveCancelButtons
                        onSave={ec.onSaveEdit}
                        onCancel={ec.onCancelEdit}
                        saving={ec.saving}
                        error={ec.saveError}
                      />
                    </td>
                  </>
                ) : (
                  <>
                    <TD right muted={r.emissions_intensity_tco2e == null}>
                      {r.emissions_intensity_tco2e ?? '—'}
                    </TD>
                    <TD right muted={r.default_frequency_years == null}>
                      {r.default_frequency_years ?? '—'}
                    </TD>
                    <TD muted={!r.source_note}>{r.source_note ?? '—'}</TD>
                    {ec && (
                      <td className="px-3 py-2 border-b border-neutral-90">
                        {ec.onDelete && (
                          <button
                            type="button"
                            onClick={() => ec.onDelete!(r.id)}
                            title="Delete row"
                            className="rounded p-0.5 cursor-pointer text-red-400 hover:text-red-600 hover:bg-red-50"
                          >
                            <span className="material-symbols-rounded text-[14px] leading-none">delete</span>
                          </button>
                        )}
                      </td>
                    )}
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
