import React, { useEffect, useMemo, useRef, useState } from "react";
import useDebounce from "../../customHooks/useDebounce";
import Info from "../../assets/icons/info.svg";

export type AutocompleteOption = {
  id?: string | number;
  label: string;
  [k: string]: any;
};

type AsyncAutocompleteProps<TOption extends AutocompleteOption> = {
  label?: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
  onSelect?: (opt: TOption) => void;
  loadOptions: () => Promise<TOption[]>;
  filterFn?: (opt: TOption, input: string) => boolean;
  id?: string;
  className?: string;
  minLength?: number;
  enableInlineCompletion?: boolean;
  icon?: React.ReactNode;
  materialIconName?: string;
  isLoginPage?: boolean;
};

const KEY = {
  UP: "ArrowUp",
  DOWN: "ArrowDown",
  ENTER: "Enter",
  ESC: "Escape",
  TAB: "Tab",
};

export default function AsyncAutocomplete<TOption extends AutocompleteOption>({
  label,
  placeholder,
  value,
  onChange,
  onSelect,
  loadOptions,
  filterFn,
  id,
  className,
  minLength = 1,
  enableInlineCompletion = true,
  icon,
  materialIconName,
  isLoginPage,
}: AsyncAutocompleteProps<TOption>) {
  const [options, setOptions] = useState<TOption[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const [error, setError] = useState<string | null>(null);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [autoOpen, setAutoOpen] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxId = `${id || "ac"}-listbox`;

  const debouncedValue = useDebounce(value, 200);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load once (cached) on first focus or first keystroke
  const ensureLoaded = async () => {
    if (loadedOnce) return;
    try {
      const data = await loadOptions();
      setOptions(data || []);
      setLoadedOnce(true);
    } catch (e: any) {
      console.error("Autocomplete loadOptions failed", e?.message ?? e);
      setError("Could not load suggestions");
    }
  };

  useEffect(() => {
    if (debouncedValue.length >= minLength) {
      ensureLoaded();
      // setOpen(true);
      if (autoOpen) setOpen(true);
    } else {
      setOpen(false);
      setActiveIndex(-1);
    }
  }, [debouncedValue, minLength]);

  const defaultFilter = (opt: TOption, input: string) =>
    opt.label.toLowerCase().includes(input.trim().toLowerCase());

  const filtered = useMemo(() => {
    const f = filterFn || defaultFilter;
    if (!debouncedValue || debouncedValue.length < minLength) return [];
    return options.filter((o) => f(o, debouncedValue)).slice(0, 20); // cap for perf
  }, [options, debouncedValue, filterFn, minLength]);

  const bestInline = useMemo(() => {
    if (!enableInlineCompletion) return null;
    if (!value || value.length < minLength) return null;
    const lower = value.toLowerCase();
    const firstStartsWith = filtered.find((o) =>
      o.label.toLowerCase().startsWith(lower)
    );
    return firstStartsWith || null;
  }, [filtered, value, minLength, enableInlineCompletion]);

  const commitSelection = (opt: TOption) => {
    setAutoOpen(false);
    onChange(opt.label);
    onSelect?.(opt);
    setOpen(false);
    setActiveIndex(-1);
    requestAnimationFrame(() => {
      if (inputRef.current) {
        const len = opt.label.length;
        inputRef.current.setSelectionRange?.(len, len);
      }
    })
  };

  // keyboard nav
  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open && [KEY.DOWN, KEY.UP].includes(e.key)) {
      setOpen(true);
      setActiveIndex(0);
      return;
    }
    switch (e.key) {
      case KEY.DOWN:
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
        break;
      case KEY.UP:
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
        break;
      case KEY.ENTER:
        if (open && activeIndex >= 0 && filtered[activeIndex]) {
          e.preventDefault();
          setAutoOpen(false);
          commitSelection(filtered[activeIndex]);
        }
        break;
      case KEY.TAB:
        if (enableInlineCompletion && bestInline) {
          // Complete to best suggestion on Tab
          setAutoOpen(false);
          onChange(bestInline.label);
          onSelect?.(bestInline);
          setOpen(false);
          setActiveIndex(-1);
        }
        break;
      case KEY.ESC:
        setOpen(false);
        setActiveIndex(-1);
        break;
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const onDocClick = (evt: MouseEvent) => {
      if (!containerRef.current) return;
      const target = evt.target as Node;
      if (!containerRef.current.contains(target)) {
        setAutoOpen(false);
        setOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const hasIcon = !!icon || !!materialIconName;
  return (
    <div ref={containerRef} className={["flex flex-col", className || ""].join(" ")}>
      {label && <label className="mb-1 text-sm text-text-base">{label}</label>}

      {/* Input wrapper for ghost text overlay */}
      <div className="relative">
        {enableInlineCompletion && open && bestInline && value && bestInline.label.toLowerCase().startsWith(value.toLowerCase()) && (
          <div className="pointer-events-none absolute rounded-[var(--radius-3)] border border-transparent px-3 py-2 text-neutral-90">
            <span className="opacity-0">{value}</span>
            {/* <span>{bestInline.label.slice(value.length)}</span> */}
          </div>
        )}

        {/* Optional left icon inside input */}
        {hasIcon && (
          <button
            type="button"
            aria-hidden="true"
            tabIndex={-1}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => inputRef.current?.focus()}
            className="absolute inset-y-0 left-0 flex cursor-pointer items-center pl-3 text-neutral-70 focus:outline-none"
          >
            {icon ? (
              <span className="pointer-events-none">{icon}</span>
            ) : (
              <span className="material-symbols-rounded pointer-events-none text-text-base">
                {materialIconName}
              </span>
            )}
          </button>
        )}

        <input
          id={id}
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => {
            setAutoOpen(true);
            onChange(e.target.value);
          }}
          onKeyDown={onKeyDown}
          onFocus={() => {
            ensureLoaded();
            if (debouncedValue.length >= minLength) setOpen(true);
          }}
          role="combobox"
          aria-autocomplete={enableInlineCompletion ? "both" : "list"}
          aria-expanded={open}
          aria-controls={listboxId}
          aria-activedescendant={
            open && activeIndex >= 0 ? `${listboxId}-opt-${activeIndex}` : undefined
          }
          placeholder={placeholder}
          className={[
            "w-full rounded-[var(--radius-3)] border border-border-input bg-white h-10 text-text-table-cell",
            // padding: if icon exists, add left padding; else default px-3
            hasIcon ? "pl-10 pr-3" : "px-3",
          ].join(" ")}

        />
      </div>

      {open && (
        <div
          id={listboxId}
          role="listbox"
          className="relative z-50 mt-1 max-h-40 overflow-auto rounded-[var(--radius-3)] border border-border-input bg-white"
        >
          {/* {error && (
            <div className="px-3 py-4 text-sm text-danger">
              {error} — you can still enter free text.
            </div>
          )} */}
        

          {isLoginPage && (
            !error && filtered.length === 0 && (
              <div className="p-4 text-sm bg-info-bg border border-info-border/35 rounded-[var(--radius-3)] flex">
                <img
                  src={Info}
                  alt="Info"
                  className="inline-block mr-2.5 mt-1 w-4.5 h-4.5 text-info-border"
                />
                <div className="flex flex-col text-info-border">
                  <div className="font-bold mb-2">
                    No matches found for {debouncedValue}
                  </div>
                  <div>
                    Click <b>Continue</b> if you wish to create this organisation
                  </div>
                </div>
              </div>
            )
          )}
          {!isLoginPage && !error && filtered.length === 0 && (
            <div className="p-3 text-sm text-text-base">
              No matches found.
            </div>
          )}
          {!error &&
            filtered.map((opt, idx) => (
              <div
                id={`${listboxId}-opt-${idx}`}
                key={opt.id ?? opt.label + idx}
                role="option"
                aria-selected={idx === activeIndex}
                onMouseDown={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  commitSelection(opt);
                }}
                className={[
                  "cursor-pointer px-3 py-2 text-sm",
                  idx === activeIndex ? "bg-neutral-100" : "bg-white",
                  "hover:bg-neutral-50",
                ].join(" ")}
              >
                {opt.label}
                {opt.email && <div className="text-xs text-text-faint mt-1">{opt.email}</div>}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}