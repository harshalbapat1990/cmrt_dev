import type { G34Row, BgmEditCtx } from '../types';
import { fmtVal } from '../utils';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

export default function Grade34Table({ rows, ec }: { rows: G34Row[]; ec?: BgmEditCtx }) {
  const isSA = !!ec;

  const startEdit = (r: G34Row) => {
    if (!ec) return;
    const key = `${r._jurisdiction_id ?? ''}||${r.emissions_category}||${r.emissions_subcategory}||${r.emissions_source}||${r.unit}`;
    ec.onStartEdit(key, {
      carbon_storage: r.carbon_storage != null ? String(r.carbon_storage) : '',
      scope1: r.scope1 != null ? String(r.scope1) : '',
      scope2: r.scope2 != null ? String(r.scope2) : '',
      scope3: r.scope3 != null ? String(r.scope3) : '',
      source: r.source,
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH normalCase>Emissions Category</TH>
          <TH normalCase>Sub-Category</TH>
          <TH normalCase>Emissions Source</TH>
          <TH normalCase>UoM</TH>
          <TH right normalCase>Carbon Storage (tCO₂e/UoM)</TH>
          <TH right normalCase>Scope 1 (tCO₂e/UoM)</TH>
          <TH right normalCase>Scope 2 (tCO₂e/UoM)</TH>
          <TH right normalCase>Scope 3 (tCO₂e/UoM)</TH>
          <TH normalCase>Source</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {ec?.adding && (
          <tr className="bg-blue-50">
            <TD><InlineSelect value={ec.addDraft.emissions_category_id ?? ''} options={ec.ecOpts} onChange={v => ec.onAddField('emissions_category_id', v)} placeholder="— cat —" /></TD>
            <TD><InlineSelect value={ec.addDraft.emissions_subcategory_id ?? ''} options={ec.ecOpts} onChange={v => ec.onAddField('emissions_subcategory_id', v)} placeholder="— subcat —" /></TD>
            <TD><InlineInput value={ec.addDraft.emissions_source ?? ''} onChange={v => ec.onAddField('emissions_source', v)} /></TD>
            <TD><InlineSelect value={ec.addDraft.unit_id ?? ''} options={ec.unitOpts} onChange={v => ec.onAddField('unit_id', v)} placeholder="— unit —" /></TD>
            <TD right><InlineInput value={ec.addDraft.carbon_storage ?? ''} onChange={v => ec.onAddField('carbon_storage', v)} type="number" /></TD>
            <TD right><InlineInput value={ec.addDraft.scope1 ?? ''} onChange={v => ec.onAddField('scope1', v)} type="number" /></TD>
            <TD right><InlineInput value={ec.addDraft.scope2 ?? ''} onChange={v => ec.onAddField('scope2', v)} type="number" /></TD>
            <TD right><InlineInput value={ec.addDraft.scope3 ?? ''} onChange={v => ec.onAddField('scope3', v)} type="number" /></TD>
            <TD><InlineInput value={ec.addDraft.source ?? ''} onChange={v => ec.onAddField('source', v)} /></TD>
            <TD><SaveCancelButtons onSave={ec.onSaveAdd} onCancel={ec.onCancelAdd} saving={ec.saving} error={ec.saveError} /></TD>
          </tr>
        )}
        {rows.map((r, i) => {
          const key = `${r._jurisdiction_id ?? ''}||${r.emissions_category}||${r.emissions_subcategory}||${r.emissions_source}||${r.unit}`;
          const isEditing = ec?.editKey === key;
          if (isEditing && ec) {
            return (
              <tr key={i} className="bg-amber-50">
                <TD muted>{r.emissions_category}</TD>
                <TD muted>{r.emissions_subcategory}</TD>
                <TD muted>{r.emissions_source}</TD>
                <TD muted>{r.unit}</TD>
                <TD right><InlineInput value={ec.editDraft.carbon_storage ?? ''} onChange={v => ec.onEditField('carbon_storage', v)} type="number" /></TD>
                <TD right><InlineInput value={ec.editDraft.scope1 ?? ''} onChange={v => ec.onEditField('scope1', v)} type="number" /></TD>
                <TD right><InlineInput value={ec.editDraft.scope2 ?? ''} onChange={v => ec.onEditField('scope2', v)} type="number" /></TD>
                <TD right><InlineInput value={ec.editDraft.scope3 ?? ''} onChange={v => ec.onEditField('scope3', v)} type="number" /></TD>
                <TD><InlineInput value={ec.editDraft.source ?? ''} onChange={v => ec.onEditField('source', v)} /></TD>
                <TD><SaveCancelButtons onSave={ec.onSaveEdit} onCancel={ec.onCancelEdit} saving={ec.saving} error={ec.saveError} /></TD>
              </tr>
            );
          }
          return (
            <tr key={i}
              className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editKey && !ec?.adding ? 'cursor-pointer' : ''}`}
              onDoubleClick={isSA && !ec?.editKey && !ec?.adding ? () => startEdit(r) : undefined}
            >
              <TD>{r.emissions_category}</TD><TD>{r.emissions_subcategory}</TD>
              <TD>{r.emissions_source}</TD>
              <TD muted>{r.unit}</TD>
              <TD right>{fmtVal(r.carbon_storage)}</TD>
              <TD right>{fmtVal(r.scope1)}</TD><TD right>{fmtVal(r.scope2)}</TD><TD right>{fmtVal(r.scope3)}</TD>
              <TD muted>{r.source}</TD>
              {isSA && (
                <TD>
                  {!ec?.editKey && !ec?.adding && (
                    <button type="button" onClick={() => startEdit(r)} title="Edit"
                      className="rounded p-0.5 cursor-pointer text-text-base hover:text-primary hover:bg-primary/10">
                      <span className="material-symbols-rounded text-[14px] leading-none">edit</span>
                    </button>
                  )}
                </TD>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
