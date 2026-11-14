import {
  bitrateMbps,
  healthStrip,
  lineSegments,
  niceCeiling,
  roundTripMs,
  type DevMetrics,
  type HealthValue,
} from "../data/dev-metrics";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import { StatusMark } from "../console/status-mark";
import styles from "./dev.module.scss";

interface HealthTilesProps {
  metrics: DevMetrics;
  samples: DevMetrics[];
  formatFps: number;
  lost: number | null;
}

interface Tile {
  labelKey: MessageKey;
  value: HealthValue;
  text: (value: number) => string;
  history: (number | null)[];
}

const SPARK_WIDTH = 120;
const SPARK_HEIGHT = 24;
const ONE_DECIMAL = 1;

export function HealthTiles({ metrics, samples, formatFps, lost }: HealthTilesProps) {
  const strip = healthStrip(metrics, formatFps, lost);
  const tiles: Tile[] = [
    {
      labelKey: "dev.fps_delivered",
      value: strip.fpsDelivered,
      text: (value) => value.toFixed(ONE_DECIMAL),
      history: samples.map((sample) => sample.delivered?.fps ?? null),
    },
    {
      labelKey: "dev.bitrate",
      value: strip.bitrateMbps,
      text: (value) => t("dev.unit_mbps", { value: value.toFixed(ONE_DECIMAL) }),
      history: samples.map(bitrateMbps),
    },
    {
      labelKey: "dev.processing_p95",
      value: strip.processingP95,
      text: (value) => t("dev.milliseconds", { value: value.toFixed(ONE_DECIMAL) }),
      history: samples.map((sample) => sample.stages?.total?.p95 ?? null),
    },
    {
      labelKey: "dev.packets_lost",
      value: strip.packetsLost,
      text: (value) => String(value),
      history: samples.map((sample) => sample.received?.packetsLost ?? null),
    },
    {
      labelKey: "dev.cpu",
      value: strip.cpuPercent,
      text: (value) => t("dev.unit_percent", { value: value.toFixed(0) }),
      history: samples.map((sample) => sample.process.cpuPercent),
    },
    {
      labelKey: "dev.round_trip",
      value: strip.roundTripMs,
      text: (value) => t("dev.milliseconds", { value: value.toFixed(0) }),
      history: samples.map(roundTripMs),
    },
  ];
  return (
    <ul className={styles.tiles}>
      {tiles.map((tile) => (
        <li key={tile.labelKey} className={styles.tile}>
          <p className={styles.tileHeader}>
            {t(tile.labelKey)}
            <span className={styles.tileHealth} data-health={tile.value.health}>
              <StatusMark
                shape={tile.value.health === "ok" ? "dot" : "triangle"}
                tone={tile.value.health === "ok" ? "live" : "warning"}
              />
              {t(tile.value.health === "ok" ? "dev.health_ok" : "dev.health_attention")}
            </span>
          </p>
          <p className={styles.tileValue} data-empty={tile.value.value === null}>
            {tile.value.value === null ? t("dev.no_data") : tile.text(tile.value.value)}
          </p>
          <svg
            className={styles.spark}
            viewBox={`0 0 ${String(SPARK_WIDTH)} ${String(SPARK_HEIGHT)}`}
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            {lineSegments(
              tile.history,
              SPARK_WIDTH,
              SPARK_HEIGHT,
              niceCeiling(Math.max(1, ...tile.history.map((value) => value ?? 0))),
            ).map((points, index) => (
              <polyline key={index} className={styles.line} data-tone="primary" points={points} />
            ))}
          </svg>
        </li>
      ))}
    </ul>
  );
}
