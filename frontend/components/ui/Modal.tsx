import { X } from "lucide-react";
import type { ReactNode } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

export function Modal({
  title,
  onClose,
  children,
  footer,
  size = "md",
}: ModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-md"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className={`card w-full ${sizeClasses[size]} shadow-modal max-h-[90vh] flex flex-col`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="card-header">
          <h2 className="text-headline-sm font-semibold text-on-background">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="btn-icon"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-lg">{children}</div>

        {footer && (
          <div className="border-t border-outline-variant px-lg py-md flex justify-end gap-sm">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
