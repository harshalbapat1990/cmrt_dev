import React, { useState, useEffect, useRef } from "react";

type NumericInputProps = {
  label?: string;
  placeholder?: string;
  value: number | string | null;
  onChange: (val: number | string | null) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  allowDecimal?: boolean;
  min?: number;
  max?:number;
  prefix?: string;
  ariaLabel?: string;
  id?: string;
  className?: string;
  onBlur?: () => void;
  autoFocus?: boolean;
  disabled?: boolean;
  allowCommaSeparated?: boolean;
  uncontrolled?: boolean;
  onCommit?: (val: string) => void;
};

export const NumericInput: React.FC<NumericInputProps> = ({
  label,
  // placeholder,
  value,
  onChange,
  onKeyDown,
  allowDecimal = false,
  allowCommaSeparated = false,
  min,
  max,
  prefix,
  ariaLabel,
  id,
  className,
  onBlur,
  autoFocus,
  disabled,
  uncontrolled = false,
  onCommit
}) => {
  const [text, setText] = useState<string>(value !== null && !Number.isNaN(value) ? String(value) : "");

  const inputRef = useRef<HTMLInputElement>(null);

  const prefixRef = useRef<HTMLSpanElement | null>(null);
  const [padLeftPx, setPadLeftPx] = useState<number>(prefix ? 0 : 12); // default ~pl-3


  useEffect(() => {
    if (uncontrolled) return;
    if (value === null || value === "") {
      setText("");
    } else {
      setText(String(value));
    }
  }, [value, uncontrolled]);


  // Measure prefix width and set input padding-left accordingly
  useEffect(() => {
    if (!prefix) {
      setPadLeftPx(12);
      return;
    }

    // SSR-safe: only run if we have a real DOM
    const g = globalThis as any;
    const el = prefixRef.current;

    const measure = () => {
      if (!el) return;
      const GAP = 8; // small gap so text doesn't touch the prefix
      setPadLeftPx(el.offsetWidth + GAP);
    };

    // Initial measure (after the span is in the DOM)
    measure();

    // Prefer ResizeObserver if available
    let ro: any = null;
    if (g && typeof g.ResizeObserver !== "undefined") {
      ro = new g.ResizeObserver(measure);
      if (el) ro.observe(el);
    } else if (g && g.addEventListener) {
      g.addEventListener("resize", measure);
    }

    return () => {
      try {
        if (ro && el) ro.unobserve(el);
        if (ro && ro.disconnect) ro.disconnect();
      } catch { }
      if (g && g.removeEventListener) {
        g.removeEventListener("resize", measure);
      }
    };
  }, [prefix]);



  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if(disabled) return;
    const next = e.target.value;

    const onlyDigits = /^[0-9]*$/;
    const digitsWithDot = /^[0-9]*([.][0-9]*)?$/;
    const digitsWithCommas = /^[0-9,\s]*$/;

    const re = allowCommaSeparated
      ? digitsWithCommas
      : (allowDecimal ? digitsWithDot : onlyDigits);

    if (!re.test(next)) return;

    setText(next);

    if (allowCommaSeparated) {
      onChange(next);
      return;
    }

    if (allowDecimal) {
      onChange(next === "" ? null : Number(next));
      return;
    }

    // Original numeric behavior:
    if (next === "") {
      onChange(null);
    } else {
      const n = Number(next);
      if (!Number.isNaN(n)) {
        onChange(n);
      } else {
        onChange(null);
      }
    }
  };


  const wrappedOnBlur = uncontrolled ? () => {
    if (onCommit && inputRef.current) {
      onCommit(inputRef.current.value);
    }
    if (onBlur) onBlur();
  } : onBlur;

  const wrappedOnKeyDown = uncontrolled ? (e: React.KeyboardEvent<HTMLInputElement>) => {
  if (disabled) {
    e.preventDefault();
    return;
  }

    if (e.key === "Enter" || e.key === "Escape") {
      if (onCommit && inputRef.current) {
        onCommit(inputRef.current.value);
      }
    }
    if (onKeyDown) onKeyDown(e);
  } : onKeyDown;

  const leftPad = prefix ? "pl-14" : "pl-3";

  return (
    <div className="w-full flex flex-col">
      {label && <label className="mb-1 text-text-base text-sm">{label}</label>}
      <div className="relative">
        {/* Left affix with right border; input text should start after this */}
        {prefix && (
          <span
            ref={prefixRef}
            className="absolute inset-y-0 left-0 w-fit px-3 inline-flex items-center justify-center text-xs text-text-base rounded-[var(--radius-3)] rounded-r-none bg-neutral-95 border border-border-input pointer-events-none select-none"
          >
            {prefix}
          </span>
        )}

        <input
          ref={inputRef}
          id={id}
          type={allowCommaSeparated ? "text" : "number"}
          inputMode={allowCommaSeparated ? "text" : (allowDecimal ? "decimal" : "numeric")}
          aria-label={ariaLabel || label}
          //   placeholder={placeholder}
          {...(uncontrolled ? { defaultValue: value ?? "" } : { value: text, onChange: handleChange })}
          onBlur={wrappedOnBlur}
          onKeyDown={wrappedOnKeyDown}
          disabled={disabled}
          readOnly={disabled}   
          autoFocus={autoFocus}
          min={min}
          max={max}
          style={{ paddingLeft: prefix ? `${padLeftPx}px` : undefined }}
          className={[`w-full h-10 block rounded-[var(--radius-3)] border border-border-input bg-white 
            ${disabled ? "pointer-events-none bg-neutral-100" : ""}
            focus:outline-none focus:ring-1 text-sm text-text-dark ${className}`, leftPad].join(" ")}
        />
      </div>
    </div>
  );
};