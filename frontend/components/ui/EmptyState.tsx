import type { ReactNode } from "react";
import { FileX } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-xl gap-md text-center">
      <div className="text-on-surface-variant opacity-40">
        {icon ?? <FileX size={40} strokeWidth={1.5} />}
      </div>
      <div>
        <p className="text-headline-sm font-semibold text-on-background">
          {title}
        </p>
        {description && (
          <p className="text-body-sm text-on-surface-variant mt-xs max-w-sm">
            {description}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}
