import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  size?: number;
  label?: string;
  className?: string;
  fullPage?: boolean;
}

export function LoadingSpinner({
  size = 20,
  label = "Loading…",
  className = "",
  fullPage = false,
}: LoadingSpinnerProps) {
  const content = (
    <div className={`flex items-center gap-sm text-on-surface-variant ${className}`}>
      <Loader2 size={size} className="animate-spin" />
      {label && <span className="text-body-sm">{label}</span>}
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        {content}
      </div>
    );
  }

  return content;
}
