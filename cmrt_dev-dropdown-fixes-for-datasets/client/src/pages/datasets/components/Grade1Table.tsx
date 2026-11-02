import type { G1Row, BgmEditCtx } from '../types';
import { fmtVal } from '../utils';
import { TH, TD, InlineInput, InlineSelect, SaveCancelButtons } from './TablePrimitives';

export default function Grade1Table({ rows, ec }: { rows: G1Row[]; ec?: BgmEditCtx }) {
  const isSA = !!ec;

  const startEdit = (r: G1Row) => {
    if (!ec) return;
    const key = `${r._jurisdiction_id ?? ''}||${r._mastertype_id ?? ''}||${r._typecast_id ?? ''}||${r._metric_type_code}`;
    ec.onStartEdit(key, {
      low:  r.low != null ? String(r.low) : '',
      mid:  r.mid != null ? String(r.mid) : '',
      high: r.high != null ? String(r.high) : '',
      source: r.source,
    });
  };

  return (
    <table className="w-full border-collapse text-xs">
      <thead className="sticky top-0 z-10 bg-neutral-90">
        <tr>
          <TH normalCase>Mastertype</TH>
          <TH normalCase>Typecast</TH>
          <TH normalCase>Metric</TH>
          <TH normalCase>Unit</TH>
          <TH normalCase>Source</TH>
          <TH right normalCase>Low</TH>
          <TH right normalCase>Mid</TH>
          <TH right normalCase>High</TH>
          {isSA && <TH>&nbsp;</TH>}
        </tr>
      </thead>
      <tbody>
        {ec?.adding && (
          <tr className="bg-blue-50">
            <TD><InlineSelect value={ec.addDraft.mastertype_id ?? ''} options={ec.mastertypeOpts} onChange={v => ec.onAddField('mastertype_id', v)} placeholder="— mastertype —" /></TD>
            <TD><InlineSelect value={ec.addDraft.typecast_id ?? ''} options={ec.typecasts.filter(t => (t as any).mastertype_id === ec.addDraft.mastertype_id)} onChange={v => ec.onAddField('typecast_id', v)} placeholder="— typecast —" /></TD>
            <TD><InlineSelect value={ec.addDraft.metric_type_id ?? ''} options={ec.metricTypeOpts} onChange={v => ec.onAddField('metric_type_id', v)} placeholder="— metric —" /></TD>
            <TD><InlineSelect value={ec.addDraft.unit_id ?? ''} options={ec.unitOpts} onChange={v => ec.onAddField('unit_id', v)} placeholder="— unit —" /></TD>
            <TD><InlineInput value={ec.addDraft.source ?? ''} onChange={v => ec.onAddField('source', v)} /></TD>
            <TD right><InlineInput value={ec.addDraft.low ?? ''} onChange={v => ec.onAddField('low', v)} type="number" /></TD>
            <TD right><InlineInput value={ec.addDraft.mid ?? ''} onChange={v => ec.onAddField('mid', v)} type="number" /></TD>
            <TD right><InlineInput value={ec.addDraft.high ?? ''} onChange={v => ec.onAddField('high', v)} type="number" /></TD>
            <TD><SaveCancelButtons onSave={ec.onSaveAdd} onCancel={ec.onCancelAdd} saving={ec.saving} error={ec.saveError} /></TD>
          </tr>
        )}
        {rows.map((r, i) => {
          const key = `${r._jurisdiction_id ?? ''}||${r._mastertype_id ?? ''}||${r._typecast_id ?? ''}||${r._metric_type_code}`;
          const isEditing = ec?.editKey === key;
          if (isEditing && ec) {
            return (
              <tr key={i} className="bg-amber-50">
                <TD muted>{r.mastertype}</TD>
                <TD muted>{r.typecast}</TD>
                <TD muted>{r.metric}</TD>
                <TD muted>{r.unit}</TD>
                <TD><InlineInput value={ec.editDraft.source ?? ''} onChange={v => ec.onEditField('source', v)} /></TD>
                <TD right><InlineInput value={ec.editDraft.low ?? ''} onChange={v => ec.onEditField('low', v)} type="number" /></TD>
                <TD right><InlineInput value={ec.editDraft.mid ?? ''} onChange={v => ec.onEditField('mid', v)} type="number" /></TD>
                <TD right><InlineInput value={ec.editDraft.high ?? ''} onChange={v => ec.onEditField('high', v)} type="number" /></TD>
                <TD><SaveCancelButtons onSave={ec.onSaveEdit} onCancel={ec.onCancelEdit} saving={ec.saving} error={ec.saveError} /></TD>
              </tr>
            );
          }
          return (
            <tr key={i}
              className={`even:bg-neutral-98 hover:bg-blue-50 ${isSA && !ec?.editKey && !ec?.adding ? 'cursor-pointer' : ''}`}
              onDoubleClick={isSA && !ec?.editKey && !ec?.adding ? () => startEdit(r) : undefined}
            >
              <TD>{r.mastertype}</TD>
              <TD>{r.typecast}</TD>
              <TD>{r.metric}</TD>
              <TD muted>{r.unit}</TD>
              <TD muted>{r.source}</TD>
              <TD right>{fmtVal(r.low)}</TD>
              <TD right>{fmtVal(r.mid)}</TD>
              <TD right>{fmtVal(r.high)}</TD>
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
