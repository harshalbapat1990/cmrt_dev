import { useState } from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export default function ConfirmDeleteRowModal({ open, onClose, onConfirm }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!open) return null;

  const handleConfirm = async () => {
    setError(null);
    setLoading(true);
    try {
      await onConfirm();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Failed to delete the row. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full mx-4">
        <div className="flex items-center gap-3 mb-4">
          <span className="material-symbols-rounded text-2xl text-danger">warning</span>
          <h2 className="text-xl font-semibold text-text-dark">Delete row</h2>
        </div>
        <p className="text-text-base mb-8">
          Are you sure you want to delete this row? This action cannot be undone.
        </p>
        {error && <p className="mb-5 text-sm text-danger" role="alert">{error}</p>}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-[var(--radius-3)] text-sm  cursor-pointer font-medium border border-neutral-300 hover:bg-neutral-50 disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={loading}
            className="px-4 py-2 rounded-[var(--radius-3)] text-sm cursor-pointer font-medium bg-danger text-white hover:bg-danger/90 disabled:opacity-60"
          >
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
