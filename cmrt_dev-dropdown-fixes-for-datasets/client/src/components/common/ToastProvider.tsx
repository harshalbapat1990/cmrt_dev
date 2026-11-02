import * as React from "react";
import Toast from "./Toast";
import type  { ToastVariant } from "./Toast";
type ToastItem = {
  id: string;
  message: string;
  variant: ToastVariant;
  duration: number; // ms
};

type ToastContextValue = {
  show: (message: string, variant?: ToastVariant, duration?: number) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
};

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const remove = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = React.useCallback(
    (message: string, variant: ToastVariant = "success", duration = 4000) => {
      const id = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2);
      const item: ToastItem = { id, message, variant, duration };
      setToasts((prev) => [item, ...prev]);

      // auto-dismiss
      window.setTimeout(() => remove(id), duration);
    },
    [remove]
  );

  const ctx: ToastContextValue = React.useMemo(
    () => ({
      show,
      success: (m, d) => show(m, "success", d),
      error: (m, d) => show(m, "error", d),
    }),
    [show]
  );

  return (
    <ToastContext.Provider value={ctx}>
      {children}

      {/* Toast stack – bottom-right */}
      <div className="
pointer-events-none fixed top-16 right-0 z-[9999]
    flex flex-col gap-3 items-end
    w-fit max-w-[90vw] pr-4
">
      {toasts.map((t) => (
        <Toast
        key={t.id}
        message={t.message}
        variant={t.variant}
        onClose={() => remove(t.id)}
        />
      ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return ctx;
}