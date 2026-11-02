export type ToastVariant = "success" | "error";

export default function Toast({
  message,
  variant = "success",
  onClose,
}: {
  message: string;
  variant?: ToastVariant;
  onClose: () => void;
}) {
  const isSuccess = variant === "success";

  const icon = isSuccess ? "check" : "close"; 
  const chipColor = isSuccess ? "bg-success" : "bg-danger";

  return (
    <div
      className={`
        pointer-events-auto
        flex items-start gap-3
        rounded-lg bg-[#333333] text-white
        shadow-[0_6px_24px_rgba(0,0,0,0.25)]
        ring-1 ring-black/10
        p-4
        w-87
        animate-in slide-in-from-right-4 fade-in-0
      `}
      role="status"
      aria-live="polite"
    >
      {/* Circular icon chip */}
      <span
        className={`
          inline-flex h-5 w-5 shrink-0 items-center justify-center
          rounded-full ${chipColor}
        `}
        aria-hidden="true"
      >
        <span className="material-symbols-rounded text-[20px] leading-none text-black/85">
          {icon}
        </span>
      </span>

      {/* Message */}
      <div className="flex-1 text-sm font-bold leading-5 text-neutral-95">
        {message}
      </div>

      {/* Close */}
      <button
        onClick={onClose}
        aria-label="Close notification"
        className="
          shrink-0 rounded p-1
          text-white/80 hover:bg-white/10 hover:text-white
          focus:outline-none focus:ring-2 focus:ring-white/30
        "
      >
        <span className="material-symbols-rounded text-[18px] leading-none">close</span>
      </button>
    </div>
  );
}
