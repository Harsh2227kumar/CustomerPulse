import type { BadgeVariant } from "@/lib/utils/format";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = "neutral", children, className = "" }: BadgeProps) {
  const cls =
    variant === "success" ? "badge-success"
    : variant === "warning" ? "badge-warning"
    : variant === "danger" ? "badge-danger"
    : variant === "info" ? "badge-info"
    : "badge-neutral";

  return <span className={`${cls} ${className}`}>{children}</span>;
}
