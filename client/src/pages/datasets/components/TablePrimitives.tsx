import type { ReactNode } from 'react';
import type { NamedOption } from '../types';

export const TH = ({ children, right, normalCase }: { children: ReactNode; right?: boolean; normalCase?: boolean }) => (
  <th className={`px-3 py-2.5 text-xs font-semibold ${normalCase ? 'normal-case' : 'uppercase'} tracking-wide text-text-base whitespace-nowrap border-r border-neutral-90 last:border-r-0 ${right ? 'text-right' : 'text-left'}`}>
    {children}
  </th>
);

export const TD = ({ children, right, muted }: { children: ReactNode; right?: boolean; muted?: boolean }) => (
  <td className={`px-3 py-2 text-xs border-r border-b border-neutral-90 last:border-r-0 ${right ? 'text-right tabular-nums' : ''} ${muted ? 'text-text-base' : 'text-text-dark'}`}>
    {children}
  </td>
);

export function InlineSelect({ value, options, onChange, placeholder }: {
  value: string; options: NamedOption[]; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full min-w-0 rounded border border-primary px-1 py-0.5 text-xs bg-white focus:outline-none"
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
    </select>
  );
}

export function InlineInput({ value, onChange, type, placeholder }: {
  value: string; onChange: (v: string) => void; type?: string; placeholder?: string;
}) {
  return (
    <input
      type={type ?? 'text'}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full min-w-0 rounded border border-primary px-1 py-0.5 text-xs focus:outline-none"
    />
  );
}

export function SaveCancelButtons({ onSave, onCancel, saving, error }: {
  onSave: () => void; onCancel: () => void; saving: boolean; error?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 items-end">
      <div className="flex gap-1">
        <button
          type="button" onClick={onSave} disabled={saving}
          className="rounded bg-primary cursor-pointer px-2 py-0.5 text-[10px] font-medium text-white disabled:opacity-40 hover:bg-primary/90"
        >{saving ? '…' : 'Save'}</button>
        <button
          type="button" onClick={onCancel}
          className="rounded border cursor-pointer border-neutral-80 bg-white px-2 py-0.5 text-[10px] font-medium text-text-base hover:bg-neutral-98"
        >Cancel</button>
      </div>
      {error && <span className="text-[10px] text-red-600 max-w-32 text-right">{error}</span>}
    </div>
  );
}
