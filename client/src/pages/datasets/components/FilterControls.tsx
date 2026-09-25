import React, { useState, useRef, useEffect } from 'react';

export function MultiSelect({ label, options, selected, onChange }: {
  label: string; options: string[]; selected: string[];
  onChange: (v: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const toggle = (v: string) =>
    onChange(selected.includes(v) ? selected.filter(x => x !== v) : [...selected, v]);
  const clearSel = (e: React.MouseEvent) => { e.stopPropagation(); onChange([]); setOpen(false); };
  const isActive = selected.length > 0;

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className={[
          'flex items-center gap-1 rounded cursor-pointer border px-2.5 py-1.5 text-xs whitespace-nowrap transition-colors h-8',
          isActive
            ? 'border-primary bg-primary/5 text-primary'
            : 'border-neutral-80 bg-white text-text-base hover:bg-neutral-98',
        ].join(' ')}
      >
        {isActive ? `${label} (${selected.length})` : label}
        {isActive && (
          <span onClick={clearSel} className="ml-0.5 px-0.5 cursor-pointer rounded-full hover:bg-primary/20 font-bold leading-none">×</span>
        )}
        <span className="material-symbols-rounded text-[14px] leading-none opacity-50">
          {open ? 'expand_less' : 'expand_more'}
        </span>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 z-50 min-w-44 max-w-72 max-h-60 overflow-y-auto bg-white border border-neutral-80 rounded shadow-lg py-1">
          {options.length === 0
            ? <p className="px-3 py-2 text-xs text-text-base italic">No options</p>
            : options.map(opt => (
                <label key={opt} className="flex items-center gap-2 px-3 py-1.5 hover:bg-neutral-98 cursor-pointer select-none">
                  <input type="checkbox" className="accent-primary"
                    checked={selected.includes(opt)} onChange={() => toggle(opt)} />
                  <span className="text-xs text-text-dark truncate" title={opt}>
                    {opt || <em className="text-text-base">blank</em>}
                  </span>
                </label>
              ))
          }
        </div>
      )}
    </div>
  );
}

export function TextFilter({ placeholder, value, onChange }: {
  placeholder: string; value: string; onChange: (v: string) => void;
}) {
  return (
    <div className="relative flex items-center">
      <span className="material-symbols-rounded absolute left-2 text-[14px] text-text-base pointer-events-none leading-none">search</span>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-8 rounded border border-neutral-80 bg-white pl-8 pr-6 py-1.5 text-xs text-text-dark placeholder:text-text-base w-36 focus:outline-none focus:border-primary transition-colors"
      />
      {value && (
        <button type="button" onClick={() => onChange('')}
          className="absolute right-1.5 cursor-pointer text-text-base hover:text-text-dark text-sm leading-none">
          ×
        </button>
      )}
    </div>
  );
}
