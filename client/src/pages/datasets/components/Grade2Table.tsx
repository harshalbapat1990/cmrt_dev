import type { G2Row, BgmEditCtx } from '../types';
import { fmtVal } from '../utils';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

export default function Grade2Table({ rows, ec }: { rows: G2Row[]; ec?: BgmEditCtx }) {
  const isSA = !!ec;

  const startEdit = (r: G2Row) => {
    if (!ec) return;
    const key = `${r._jurisdiction_id ?? ''}||${r.emissions_category}||${r.emissions_subcategory}||${r.emissions_source}||${r.unit}`;
    ec.onStartEdit(key, {
      quantity: r.quantity != null ? String(r.quantity) : '',
      carbon_storage: r.carbon_storage != null ? String(r.carbon_storage) : '',
      a1_a3: r.a1_a3 != null ? String(r.a1_a3) : '',
      a4: r.a4 != null ? String(r.a4) : '',
      a5: r.a5 != null ? String(r.a5) : '',
      source: r.source,
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH normalCase>
            Emissions Category
          </TH>
          <TH normalCase>
            Sub-Category
          </TH>
          <TH normalCase>
            Emissions Source
          </TH>
          <TH right normalCase>
            Qty
          </TH>
          <TH normalCase>
            UoM
          </TH>
          <TH right normalCase>
            Carbon Storage
            <span className="block text-xs text-neutral-60">
              (tCO₂e / UoM)
            </span>
          </TH>
          <TH right normalCase>
            Product Stage (A1–3)
            <span className="block text-xs text-neutral-60">
              Emissions Factor
            </span>
            <span className="block text-xs text-neutral-60">
              (tCO₂e / UoM)
            </span>
          </TH>
          <TH right normalCase>
            Transport Stage (A4)
            <span className="block text-xs text-neutral-60">
              Emissions Factor
            </span>
            <span className="block text-xs text-neutral-60">
              (tCO₂e / UoM)
            </span>
          </TH>
          <TH right normalCase>
            Construction Stage (A5)
            <span className="block text-xs text-neutral-60">
              Emissions Factor
            </span>
            <span className="block text-xs text-neutral-60">
              (tCO₂e / UoM)
            </span>
          </TH>
          <TH normalCase>
            Source
          </TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {ec?.adding && (
          <tr className="bg-blue-50">
            <TD><InlineSelect value={ec.addDraft.emissions_category_id ?? ''} options={ec.ecOpts} onChange={v => ec.onAddField('emissions_category_id', v)} placeholder="" /></TD>
            <TD><InlineSelect value={ec.addDraft.emissions_subcategory_id ?? ''} options={ec.ecOpts} onChange={v => ec.onAddField('emissions_subcategory_id', v)} placeholder="" /></TD>
            <TD><InlineInput value={ec.addDraft.emissions_source ?? ''} onChange={v => ec.onAddField('emissions_source', v)} /></TD>
            <TD right><InlineInput value={ec.addDraft.assumed_quantity_default ?? ''} onChange={v => ec.onAddField('assumed_quantity_default', v)} type="number" /></TD>
            <TD><InlineSelect value={ec.addDraft.unit_id ?? ''} options={ec.unitOpts} onChange={v => ec.onAddField('unit_id', v)} placeholder="" /></TD>
            <TD right><InlineInput value={ec.addDraft.carbon_storage ?? ''} onChange={v => ec.onAddField('carbon_storage', v)} type="number" /></TD>
            <TD right><InlineInput value={ec.addDraft.a1_a3 ?? ''} onChange={v => ec.onAddField('a1_a3', v)} type="number" /></TD>
            <TD right><InlineInput value={ec.addDraft.a4 ?? ''} onChange={v => ec.onAddField('a4', v)} type="number" /></TD>
            <TD right><InlineInput value={ec.addDraft.a5 ?? ''} onChange={v => ec.onAddField('a5', v)} type="number" /></TD>
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
                <TD right><InlineInput value={ec.editDraft.quantity ?? ''} onChange={v => ec.onEditField('quantity', v)} type="number" /></TD>
                <TD muted>{r.unit}</TD>
                <TD right><InlineInput value={ec.editDraft.carbon_storage ?? ''} onChange={v => ec.onEditField('carbon_storage', v)} type="number" /></TD>
                <TD right><InlineInput value={ec.editDraft.a1_a3 ?? ''} onChange={v => ec.onEditField('a1_a3', v)} type="number" /></TD>
                <TD right><InlineInput value={ec.editDraft.a4 ?? ''} onChange={v => ec.onEditField('a4', v)} type="number" /></TD>
                <TD right><InlineInput value={ec.editDraft.a5 ?? ''} onChange={v => ec.onEditField('a5', v)} type="number" /></TD>
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
              <TD>{r.emissions_category}</TD>
              <TD>{r.emissions_subcategory}</TD>
              <TD>{r.emissions_source}</TD>
              <TD right>{fmtVal(r.quantity)}</TD>
              <TD muted>{r.unit}</TD>
              <TD right>{fmtVal(r.carbon_storage)}</TD>
              <TD right>{fmtVal(r.a1_a3)}</TD>
              <TD right>{fmtVal(r.a4)}</TD>
              <TD right>{fmtVal(r.a5)}</TD>
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
