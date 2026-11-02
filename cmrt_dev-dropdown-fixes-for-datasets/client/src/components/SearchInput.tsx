import React from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}

const SearchInput: React.FC<Props> = ({ value, onChange, placeholder, className }) => {
  // Clear the input (and inform parent)
  const handleClear = () => onChange("");

  // Support ESC to clear
  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Escape" && value) {
      e.preventDefault();
      handleClear();
    }
  };

  return (
    <div className={`relative ${className ?? ""} `}>
      {/* Search icon (left) */}
      <span className="material-symbols-rounded absolute left-3 top-2 text-text-dark text-base pointer-events-none">
        search
      </span>

      {/* Input */}
      <input
        type="text"
        placeholder={placeholder ?? "Search"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        className="w-full border border-border-input rounded-[var(--radius-3)] pl-11 pr-10 py-2 text-sm text-gray-800 placeholder-gray-400 h-10   
          transition-[border-color,box-shadow] duration-150"
        aria-label={placeholder ?? "Search"}

        autoComplete="off"
      />

      {/* Cancel / Clear button (right) — shown only when there is text */}
      {value?.length > 0 && (
        <button
          type="button"
          onClick={handleClear}
          aria-label="Clear search"
          title="Clear"
          className={[
            "absolute text-sm right-3 top-2.5",
            "flex items-center justify-center",
            "h-5 w-5 rounded-full",
            "text-text-faint hover:text-text-dark cursor-pointer",
            "focus:outline-none focus:ring-2 focus:ring-blue-500",
          ].join(" ")}
        >
          <span className="material-symbols-rounded text-base leading-none">
            close
          </span>
        </button>
      )}
    </div>
  );
};

export default SearchInput;