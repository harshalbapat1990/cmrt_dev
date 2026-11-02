import type { ChangeEvent } from "react";

interface Props {
  isNotes: boolean;
  value: string;
  onValueChange: (value: string) => void;
  dirty: boolean;
  author: string | null;
  date: string | null;
  characterLimit: number;
  readOnly: boolean;
  onSave: () => void;
}

export function ExecutiveSummaryPanel({
  isNotes,
  value,
  onValueChange,
  dirty,
  author,
  date,
  characterLimit,
  readOnly,
  onSave,
}: Props) {
  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    onValueChange(event.currentTarget.value.slice(0, characterLimit));
  };

  const formattedDate = date
    ? new Date(date).toLocaleDateString("en-AU", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <div className="border border-neutral-90 bg-white p-6 rounded-[var(--radius-3)] mx-12 mb-12">
      <div className="mb-2">
        <label className="text-sm text-text-base font-medium">
          {isNotes ? "Notes/comments" : "Executive summary"}{" "}
          <span className="font-normal">(optional)</span>
        </label>
        <div className="text-xs text-text-faint">
          {value.length}/{characterLimit}
        </div>
      </div>
      <textarea
        className={`border border-border-input w-full rounded-[var(--radius-3)] h-32 p-3 outline-none focus:ring-2 focus:ring-border-input focus:border-transparent ${readOnly ? "bg-neutral-95" : ""}`}
        value={value}
        onChange={handleChange}
        maxLength={characterLimit}
        aria-label={isNotes ? "Notes/comments" : "Executive summary"}
        disabled={readOnly}
      />
      {!dirty && value && (author || formattedDate) && (
        <div className="text-xs text-neutral-400 mt-1">
          {[author, formattedDate].filter(Boolean).join(" • ")}
        </div>
      )}
      {!readOnly && (
        <div className="flex justify-end mt-3">
          <button
            type="button"
            disabled={!dirty}
            onClick={onSave}
            className="px-4 py-2 text-sm font-medium cursor-pointer rounded-[var(--radius-3)] bg-primary text-white disabled:opacity-40 hover:bg-primary/90 transition-colors"
          >
            Save
          </button>
        </div>
      )}
    </div>
  );
}
