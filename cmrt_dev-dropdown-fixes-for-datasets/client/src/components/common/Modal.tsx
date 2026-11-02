import React, { useCallback, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

type ModalProps = {
  isOpen: boolean;
  onClose: () => void;
  title?: string; // for aria-labelledby
  children: React.ReactNode;
  /** Optional: prevent closing via backdrop/ESC */
  disableBackdropClose?: boolean;
  disableEscClose?: boolean;
  /** Optional: center vs custom layout */
  className?: string;
};

/**
 * Accessible Modal:
 * - Renders in a portal (to document.body)
 * - Focus trap & return focus to opener
 * - ESC to close, click backdrop to close
 * - aria-modal, role=dialog, aria-labelledby
 * - Body scroll lock when open
 */
export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  disableBackdropClose,
  disableEscClose,
  className = "",
}) => {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const lastFocusedRef = useRef<HTMLElement | null>(null);

  // Create/get modal root
  const modalRoot = getOrCreateModalRoot();

  // Handle ESC key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape" && !disableEscClose) {
        e.stopPropagation();
        onClose();
      }
      // Basic focus trap: cycle focus within dialog
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = getFocusable(dialogRef.current);
        if (focusable.length === 0) return;

        const first = focusable[0] as HTMLElement;
        const last = focusable[focusable.length - 1] as HTMLElement;

        const isShift = e.shiftKey;
        const active = document.activeElement as HTMLElement | null;

        if (!isShift && active === last) {
          e.preventDefault();
          first.focus();
        } else if (isShift && active === first) {
          e.preventDefault();
          last.focus();
        }
      }
    },
    [isOpen, disableEscClose, onClose]
  );

  // Open/close side effects
  useEffect(() => {
    if (isOpen) {
      // Save last focused element to restore on close
      lastFocusedRef.current = document.activeElement as HTMLElement | null;

      // Lock body scroll
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";

      // Listen for keydown
      document.addEventListener("keydown", handleKeyDown);

      // Move focus into dialog
      const timer = setTimeout(() => {
        if (!dialogRef.current) return;
        const focusable = getFocusable(dialogRef.current);
        if (focusable.length > 0) {
          (focusable[0] as HTMLElement).focus();
        } else {
          dialogRef.current.focus();
        }
      }, 0);

      return () => {
        clearTimeout(timer);
        document.removeEventListener("keydown", handleKeyDown);
        document.body.style.overflow = prevOverflow;
        // Restore focus to previously focused element
        if (lastFocusedRef.current) lastFocusedRef.current.focus();
      };
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (disableBackdropClose) return;
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  const dialogAria = {
    role: "dialog",
    "aria-modal": true,
    ...(title ? { "aria-labelledby": "modal-title" } : {}),
  };

  return createPortal(
    <div
      ref={overlayRef}
      onMouseDown={handleBackdropClick}
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 backdrop-blur-[1px] overflow-y-scroll"
      aria-hidden={!isOpen}
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        {...dialogAria}
        className={[
          // container
          "relative w-full  rounded-[var(--radius-3)] bg-white p-0 shadow-xl outline-none",
          "animate-in fade-in zoom-in-95 duration-150",
          className || "",
        ].join(" ")}
      >
        {/* Body (content from children) */}
        <div>{children}</div>
      </div>
    </div>,
    modalRoot
  );
};

// Utilities

function getOrCreateModalRoot(): HTMLElement {
  let root = document.getElementById("modal-root");
  if (!root) {
    root = document.createElement("div");
    root.setAttribute("id", "modal-root");
    document.body.appendChild(root);
  }
  return root;
}

function getFocusable(container: HTMLElement): Element[] {
  const selectors = [
    "a[href]",
    "area[href]",
    'input:not([disabled]):not([type="hidden"])',
    "select:not([disabled])",
    "textarea:not([disabled])",
    "button:not([disabled])",
    "iframe",
    "object",
    "embed",
    "[tabindex]:not([tabindex='-1'])",
    "[contenteditable=true]",
  ];
  return Array.from(container.querySelectorAll(selectors.join(","))).filter(
    (el) => (el as HTMLElement).offsetParent !== null || el === document.activeElement
  );
}