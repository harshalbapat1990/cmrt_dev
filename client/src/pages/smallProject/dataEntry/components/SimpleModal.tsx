import type { ReactNode } from "react";

interface SimpleModalProps {
    open: boolean;
    title: string;
    children: ReactNode;
    onClose?: () => void;
}

export const SimpleModal = ({ open, title, children }: SimpleModalProps) => {
    if (!open) return null;
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-lg w-full mx-4">
                <div className="text-2xl text-text-dark mb-6">{title}</div>
                <div className="mb-6">{children}</div>
            </div>
        </div>
    );
};
