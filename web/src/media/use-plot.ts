import { useEffect, useRef, type RefObject } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";

export interface PlotTheme {
  data: string;
  data2: string;
  data3: string;
  grid: string;
  reference: string;
  warning: string;
  negative: string;
  pixelRatio: number;
}

export type PlotOptions = Omit<uPlot.Options, "width" | "height">;
export type PlotBuilder<T> = (theme: PlotTheme, current: () => T) => PlotOptions;

const THEME_TOKENS = {
  data: "--data",
  data2: "--data-2",
  data3: "--data-3",
  grid: "--grid",
  reference: "--reference",
  warning: "--warning",
  negative: "--negative",
} as const;

export function usePlot<T>(
  build: PlotBuilder<T>,
  data: uPlot.AlignedData,
  extras: T,
): RefObject<HTMLDivElement | null> {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const plotRef = useRef<uPlot | null>(null);
  const buildRef = useRef(build);
  const dataRef = useRef(data);
  const extrasRef = useRef(extras);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const options = buildRef.current(plotTheme(), () => extrasRef.current);
    const plot = new uPlot({ ...options, ...sizeOf(container) }, dataRef.current, container);
    plotRef.current = plot;
    const observer = new ResizeObserver(() => {
      plot.setSize(sizeOf(container));
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      plot.destroy();
      plotRef.current = null;
    };
  }, []);

  useEffect(() => {
    dataRef.current = data;
    extrasRef.current = extras;
    plotRef.current?.setData(data);
  }, [data, extras]);

  return containerRef;
}

function sizeOf(container: HTMLElement): { width: number; height: number } {
  return { width: container.clientWidth, height: container.clientHeight };
}

function plotTheme(): PlotTheme {
  const style = getComputedStyle(document.documentElement);
  const colors = Object.fromEntries(
    Object.entries(THEME_TOKENS).map(([name, token]) => [name, style.getPropertyValue(token).trim()]),
  ) as Record<keyof typeof THEME_TOKENS, string>;
  return { ...colors, pixelRatio: uPlot.pxRatio };
}
