"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";
type ChartOption = Parameters<echarts.ECharts["setOption"]>[0];

interface EChartProps {
  option: echarts.EChartsCoreOption;
  height?: number;
  onClick?: (params: unknown) => void;
}

export function EChart({ option, height = 280, onClick }: EChartProps) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!elementRef.current) return;
    chartRef.current = echarts.init(elementRef.current, undefined, { renderer: "canvas" });

    const resize = () => chartRef.current?.resize();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option as ChartOption, true);
  }, [option]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !onClick) return;
    chart.on("click", onClick);
    return () => {
      chart.off("click", onClick);
    };
  }, [onClick]);

  return <div ref={elementRef} style={{ width: "100%", height }} />;
}
