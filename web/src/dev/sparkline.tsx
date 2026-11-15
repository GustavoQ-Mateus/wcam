import { useMemo, useState } from "react";
import type uPlot from "uplot";
import { chartIndexes, clampedColumn } from "../data/chart-data";
import { niceCeiling } from "../data/dev-metrics";
import { usePlot } from "../media/use-plot";
import styles from "./dev.module.scss";
import { sparklineOptions } from "./plot-options";

interface SparklineProps {
  history: (number | null)[];
}

export function Sparkline({ history }: SparklineProps) {
  const [build] = useState(sparklineOptions);
  const max = niceCeiling(Math.max(1, ...history.map((value) => value ?? 0)));
  const data = useMemo(
    () => [chartIndexes(history.length), clampedColumn(history, max)] as uPlot.AlignedData,
    [history, max],
  );
  const extras = useMemo(() => ({ max }), [max]);
  const plotRef = usePlot(build, data, extras);
  return <div ref={plotRef} className={styles.spark} aria-hidden="true" />;
}
