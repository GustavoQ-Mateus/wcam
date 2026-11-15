import { useMemo, useState, type PointerEvent } from "react";
import type uPlot from "uplot";
import { lineChartColumns } from "../data/chart-data";
import type { ChartMark } from "../data/dev-view";
import { usePlot } from "../media/use-plot";
import styles from "./dev.module.scss";
import { lineChartOptions, type ChartTone, type LineChartExtras } from "./plot-options";

export interface ChartSeries {
  label: string;
  values: (number | null)[];
  tone: ChartTone;
}

export interface ChartBand {
  label: string;
  values: number[];
  tone: ChartTone;
}

export interface ChartReference {
  label: string;
  value: number;
}

interface LineChartProps {
  title: string;
  series: ChartSeries[];
  bands?: ChartBand[];
  max: number;
  reference?: ChartReference;
  marks: ChartMark[];
  markLegend?: { label: string; kind: ChartMark["kind"] }[];
  format: (value: number) => string;
  startLabel: string;
  endLabel: string;
}

const PERCENT = 100;

export function LineChart({
  title,
  series,
  bands = [],
  max,
  reference,
  marks,
  markLegend = [],
  format,
  startLabel,
  endLabel,
}: LineChartProps) {
  const [hover, setHover] = useState<number | null>(null);
  const [build] = useState(() =>
    lineChartOptions(
      bands.map((band) => band.tone),
      series.map((line) => line.tone),
      reference !== undefined,
    ),
  );
  const referenceValue = reference?.value ?? null;
  const data = useMemo(() => {
    const columns = lineChartColumns(
      series.map((line) => line.values),
      bands.map((band) => band.values),
      max,
      referenceValue,
    );
    return [
      columns.indexes,
      ...columns.bands,
      ...(columns.reference ? [columns.reference] : []),
      ...columns.lines,
    ] as uPlot.AlignedData;
  }, [series, bands, max, referenceValue]);
  const extras = useMemo<LineChartExtras>(() => ({ max, marks }), [max, marks]);
  const plotRef = usePlot(build, data, extras);
  const count = series[0]?.values.length ?? bands[0]?.values.length ?? 0;
  const keyed = [...bands, ...series];
  const onMove = (event: PointerEvent<HTMLDivElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const share = (event.clientX - box.left) / box.width;
    setHover(count > 1 ? Math.round(share * (count - 1)) : null);
  };
  const hoverShare = hover !== null && count > 1 ? hover / (count - 1) : null;
  return (
    <section className={styles.chart}>
      <header className={styles.chartHeader}>
        <h2 className={styles.chartTitle}>{title}</h2>
        <ul className={styles.legend}>
          {keyed.map((line) => (
            <li key={line.label} className={styles.legendItem}>
              <span className={styles.swatch} data-tone={line.tone} aria-hidden="true" />
              {line.label}
            </li>
          ))}
          {markLegend.map((item) => (
            <li key={item.label} className={styles.legendItem}>
              <span className={styles.swatch} data-tone={item.kind} aria-hidden="true" />
              {item.label}
            </li>
          ))}
          {reference && (
            <li className={styles.legendItem}>
              <span className={styles.swatch} data-tone="reference" aria-hidden="true" />
              {reference.label}
            </li>
          )}
        </ul>
      </header>
      <div className={styles.plot}>
        <span className={styles.axisTop}>{format(max)}</span>
        <div
          ref={plotRef}
          className={styles.svg}
          role="img"
          aria-label={title}
          onPointerMove={onMove}
          onPointerLeave={() => {
            setHover(null);
          }}
        />
        {hoverShare !== null && (
          <div className={styles.crosshair} style={{ insetInlineStart: `${String(hoverShare * PERCENT)}%` }} />
        )}
        {hover !== null && (
          <div className={styles.tooltip} style={{ insetInlineStart: `${String((hoverShare ?? 0) * PERCENT)}%` }}>
            {keyed.map((line) => {
              const value = line.values[hover];
              return (
                <p key={line.label}>
                  <span className={styles.swatch} data-tone={line.tone} aria-hidden="true" />
                  {line.label} {value === null || value === undefined ? "" : format(value)}
                </p>
              );
            })}
          </div>
        )}
      </div>
      <footer className={styles.axisBottom}>
        <span>{startLabel}</span>
        <span>{endLabel}</span>
      </footer>
    </section>
  );
}
