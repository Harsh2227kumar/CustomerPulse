import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  valueClassName?: string;
}

export function StatCard({ label, value, sub, valueClassName = "" }: StatCardProps) {
  return (
    <div className="stat-card min-w-0">
      <span className="text-label-md text-on-surface-variant uppercase tracking-wider block">
        {label}
      </span>
      <div className="flex items-baseline gap-xs mt-xs">
        <span
          className={`text-headline-lg font-bold text-on-background ${valueClassName}`}
        >
          {value}
        </span>
        {sub && (
          <span className="text-body-sm text-surface-tint">{sub}</span>
        )}
      </div>
    </div>
  );
}
