"use client";

import type { TrendPoint } from "@/lib/api/types";

interface TrendChartProps {
  data: TrendPoint[];
  height?: number;
  color?: string;
  label?: string;
}

export function TrendChart({
  data,
  height = 120,
  color = "#0f172a",
  label = "Trend",
}: TrendChartProps) {
  if (!data.length) {
    return (
      <div
        className="flex items-center justify-center text-on-surface-variant text-body-sm"
        style={{ height }}
      >
        No trend data available
      </div>
    );
  }

  const values = data.map((d) => d.count);
  const maxVal = Math.max(...values, 1);
  const minVal = Math.min(...values, 0);
  const range = maxVal - minVal || 1;

  const W = 600;
  const H = 100;
  const paddingX = 8;
  const paddingY = 8;

  const points = values.map((v, i) => {
    const x =
      values.length === 1
        ? W / 2
        : paddingX + (i * (W - paddingX * 2)) / (values.length - 1);
    const y = H - paddingY - ((v - minVal) / range) * (H - paddingY * 2);
    return `${x},${y}`;
  });

  const polyline = points.join(" ");
  const fillPath = `M${points[0]} ${points.slice(1).map((p) => `L${p}`).join(" ")} L${points[points.length - 1].split(",")[0]},${H} L${points[0].split(",")[0]},${H} Z`;

  return (
    <div className="w-full" style={{ height }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="w-full h-full"
        role="img"
        aria-label={label}
      >
        <defs>
          <linearGradient id={`fill-${label}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.15" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
          {/* Dashed grid lines */}
        </defs>
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((fraction) => (
          <line
            key={fraction}
            x1={paddingX}
            x2={W - paddingX}
            y1={paddingY + fraction * (H - paddingY * 2)}
            y2={paddingY + fraction * (H - paddingY * 2)}
            stroke="#e2e8f0"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
        ))}
        {/* Fill area */}
        <path d={fillPath} fill={`url(#fill-${label})`} />
        {/* Line */}
        <polyline
          points={polyline}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Dots on data points (when few points) */}
        {values.length <= 12 &&
          points.map((point, i) => {
            const [x, y] = point.split(",").map(Number);
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r="3"
                fill={color}
                stroke="white"
                strokeWidth="1.5"
              />
            );
          })}
      </svg>
    </div>
  );
}
