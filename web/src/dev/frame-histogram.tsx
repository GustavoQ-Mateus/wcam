import { histogram } from "../data/dev-metrics";
import { t } from "../data/language";
import styles from "./dev.module.scss";

interface FrameHistogramProps {
  frameTimes: number[];
  budgetMs: number | null;
  median: number | null;
  p95: number | null;
}

const BIN_MS = 2;
const MAX_MS = 50;
const WIDTH = 300;
const HEIGHT = 120;
const BAR_GAP = 2;
const ONE_DECIMAL = 1;

export function FrameHistogram({ frameTimes, budgetMs, median, p95 }: FrameHistogramProps) {
  const bins = histogram(frameTimes, BIN_MS, MAX_MS);
  const tallest = Math.max(1, ...bins);
  const binWidth = WIDTH / bins.length;
  const ms = (value: number | null) =>
    value === null ? t("dev.not_reported") : t("dev.milliseconds", { value: value.toFixed(ONE_DECIMAL) });
  return (
    <section className={styles.panel}>
      <h2 className={styles.chartTitle}>{t("dev.histogram")}</h2>
      <svg
        className={styles.histogram}
        viewBox={`0 0 ${String(WIDTH)} ${String(HEIGHT)}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={t("dev.histogram")}
      >
        {bins.map((count, index) => (
          <rect
            key={index}
            className={styles.bar}
            x={index * binWidth}
            y={HEIGHT - (count / tallest) * HEIGHT}
            width={Math.max(0, binWidth - BAR_GAP)}
            height={(count / tallest) * HEIGHT}
          />
        ))}
        {budgetMs !== null && (
          <line
            className={styles.reference}
            x1={(Math.min(budgetMs, MAX_MS) / MAX_MS) * WIDTH}
            x2={(Math.min(budgetMs, MAX_MS) / MAX_MS) * WIDTH}
            y1="0"
            y2={HEIGHT}
          />
        )}
      </svg>
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
