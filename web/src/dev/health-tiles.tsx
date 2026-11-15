import { bitrateMbps, healthStrip, roundTripMs, type DevMetrics, type HealthValue } from "../data/dev-metrics";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import { StatusMark } from "../console/status-mark";
import styles from "./dev.module.scss";
import { Sparkline } from "./sparkline";

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
          <Sparkline history={tile.history} />
        </li>
      ))}
    </ul>
  );
}
