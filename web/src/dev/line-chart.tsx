import { useState, type PointerEvent } from "react";
import { lineSegments, stackedBands } from "../data/dev-metrics";
import type { ChartMark } from "../data/dev-view";
import styles from "./dev.module.scss";

export interface ChartSeries {
  label: string;
  values: (number | null)[];
  tone: "primary" | "secondary" | "tertiary";
}

export interface ChartBand {
  label: string;
  values: number[];
  tone: "primary" | "secondary" | "tertiary";
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

export const CHART_WIDTH = 600;
export const CHART_HEIGHT = 160;
const GRID_LINES = [0.25, 0.5, 0.75];

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
  const count = series[0]?.values.length ?? bands[0]?.values.length ?? 0;
  const keyed = [...bands, ...series];
  const onMove = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const share = (event.clientX - box.left) / box.width;
    setHover(count > 1 ? Math.round(share * (count - 1)) : null);
  };
  const hoverX = hover !== null && count > 1 ? (hover / (count - 1)) * CHART_WIDTH : null;
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
        <svg
          className={styles.svg}
          viewBox={`0 0 ${String(CHART_WIDTH)} ${String(CHART_HEIGHT)}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={title}
          onPointerMove={onMove}
          onPointerLeave={() => {
            setHover(null);
          }}
        >
          {GRID_LINES.map((share) => (
            <line
              key={share}
              className={styles.gridLine}
              x1="0"
              x2={CHART_WIDTH}
              y1={share * CHART_HEIGHT}
              y2={share * CHART_HEIGHT}
            />
          ))}
          {marks.map((mark, index) => (
            <line
              key={index}
              className={styles.mark}
              data-kind={mark.kind}
              x1={mark.share * CHART_WIDTH}
              x2={mark.share * CHART_WIDTH}
              y1="0"
              y2={CHART_HEIGHT}
            />
          ))}
          {stackedBands(
            bands.map((band) => band.values),
            CHART_WIDTH,
            CHART_HEIGHT,
            max,
          ).map((points, index) => (
            <polygon key={bands[index]?.label} className={styles.band} data-tone={bands[index]?.tone} points={points} />
          ))}
          {reference && (
            <line
              className={styles.reference}
              x1="0"
              x2={CHART_WIDTH}
              y1={CHART_HEIGHT - (Math.min(reference.value, max) / max) * CHART_HEIGHT}
              y2={CHART_HEIGHT - (Math.min(reference.value, max) / max) * CHART_HEIGHT}
            />
          )}
          {series.map((line) =>
            lineSegments(line.values, CHART_WIDTH, CHART_HEIGHT, max).map((points, index) => (
              <polyline
                key={`${line.label}-${String(index)}`}
                className={styles.line}
                data-tone={line.tone}
                points={points}
              />
            )),
          )}
          {hoverX !== null && <line className={styles.crosshair} x1={hoverX} x2={hoverX} y1="0" y2={CHART_HEIGHT} />}
        </svg>
        {hover !== null && (
          <div
            className={styles.tooltip}
            style={{ insetInlineStart: `${String(((hoverX ?? 0) / CHART_WIDTH) * 100)}%` }}
          >
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
