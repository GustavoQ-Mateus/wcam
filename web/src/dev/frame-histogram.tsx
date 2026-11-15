import { useMemo, useState } from "react";
import type uPlot from "uplot";
import { chartIndexes } from "../data/chart-data";
import { histogram } from "../data/dev-metrics";
import { t } from "../data/language";
import { usePlot } from "../media/use-plot";
import styles from "./dev.module.scss";
import { histogramOptions, type HistogramExtras } from "./plot-options";

interface FrameHistogramProps {
  frameTimes: number[];
  budgetMs: number | null;
  median: number | null;
  p95: number | null;
}

const BIN_MS = 2;
const MAX_MS = 50;
const ONE_DECIMAL = 1;

export function FrameHistogram({ frameTimes, budgetMs, median, p95 }: FrameHistogramProps) {
  const [build] = useState(histogramOptions);
  const bins = useMemo(() => histogram(frameTimes, BIN_MS, MAX_MS), [frameTimes]);
  const data = useMemo(() => [chartIndexes(bins.length), bins] as uPlot.AlignedData, [bins]);
  const budgetShare = budgetMs === null ? null : Math.min(budgetMs, MAX_MS) / MAX_MS;
  const extras = useMemo<HistogramExtras>(() => ({ binCount: bins.length, budgetShare }), [bins.length, budgetShare]);
  const plotRef = usePlot(build, data, extras);
  const ms = (value: number | null) =>
    value === null ? t("dev.not_reported") : t("dev.milliseconds", { value: value.toFixed(ONE_DECIMAL) });
  return (
    <section className={styles.panel}>
      <h2 className={styles.chartTitle}>{t("dev.histogram")}</h2>
      <div ref={plotRef} className={styles.histogram} role="img" aria-label={t("dev.histogram")} />
      <footer className={styles.axisBottom}>
        <span>{t("dev.milliseconds", { value: "0" })}</span>
        <span>
          p50 {ms(median)} · p95 {ms(p95)}
        </span>
        <span>{t("dev.milliseconds", { value: String(MAX_MS) })}</span>
      </footer>
    </section>
  );
}
