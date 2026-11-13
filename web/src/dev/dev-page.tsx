import { useState } from "react";
import { consoleMode, stateBadge } from "../data/console-view";
import {
  keyFrameIntervalSeconds,
  lastSeconds,
  metricsCsv,
  niceCeiling,
  packetsLostIn,
  percentile,
  type DevMetrics,
} from "../data/dev-metrics";
import { devCharts, liveDuration, stageMedians } from "../data/dev-view";
import { t } from "../data/language";
import { useConsole } from "../data/use-console";
import { useDevEvents } from "../data/use-dev-events";
import { downloadText } from "../media/download-text";
import { usePreview } from "../media/use-preview";
import { PreviewPanel } from "../console/preview-panel";
import { StatusMark } from "../console/status-mark";
import { DetailList } from "./detail-list";
import styles from "./dev.module.scss";
import { EventList } from "./event-list";
import { FramePath } from "./frame-path";
import { FrameHistogram } from "./frame-histogram";
import { HealthTiles } from "./health-tiles";
import { LineChart } from "./line-chart";
import { PreviewControls } from "./preview-controls";

const WINDOWS = [30, 60, 120] as const;
const DEFAULT_WINDOW = 60;
const FPS_DECIMALS = 1;
const MS_DECIMALS = 1;
const MIN_FPS_SCALE = 30;
const CSV_NAME = "wcam-metrics.csv";
const CONSOLE_PATH = "/";
const MILLISECONDS_PER_SECOND = 1000;
const KILOBITS_PER_MEGABIT = 1000;
const MEDIAN = 0.5;
const P95 = 0.95;
const CAMERA_KEYS = { user: "camera.front", environment: "camera.back" } as const;

export default function DevPage() {
  const consoleData = useConsole();
  const live = useDevEvents();
  const [windowSeconds, setWindowSeconds] = useState<number>(DEFAULT_WINDOW);
  const [paused, setPaused] = useState<DevMetrics[] | null>(null);
  const preview = usePreview(true);
  const samples = paused ?? live.samples;
  const shown = lastSeconds(samples, windowSeconds);
  const latest = shown[shown.length - 1];
  const charts = devCharts(shown, live.events);
  const status = consoleData.status;
  const mode = status ? consoleMode(status) : null;
  const badge = status ? stateBadge(status) : null;
  const formatFps = latest ? Math.round(MILLISECONDS_PER_SECOND / latest.budgetMs) : MIN_FPS_SCALE;
  const frameTimes = shown.flatMap((sample) => sample.frameTimesMs ?? []);
  const fps = (value: number) => t("dev.unit_fps", { value: value.toFixed(FPS_DECIMALS) });
  const ms = (value: number) => t("dev.milliseconds", { value: value.toFixed(MS_DECIMALS) });
  const mbps = (value: number) => t("dev.unit_mbps", { value: value.toFixed(FPS_DECIMALS) });
  const ago = t("dev.seconds_ago", { seconds: String(windowSeconds) });
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div className={styles.identity}>
          <a className={styles.back} href={CONSOLE_PATH}>
            {t("app.name")}
          </a>
          <h1 className={styles.title}>{t("dev.title")}</h1>
          {badge && (
            <p className={styles.badge} data-tone={badge.tone}>
              <StatusMark shape={badge.shape} tone={badge.tone} />
              {badge.tone === "live" && latest?.session?.liveSince
                ? t("dev.live_for", { duration: liveDuration(latest.session.liveSince, latest.at) })
                : t(badge.key)}
            </p>
          )}
          {latest?.session && (
            <p className={styles.meta}>
              {[
                latest.session.deviceName,
                latest.session.facing && t(CAMERA_KEYS[latest.session.facing]),
                latest.session.format,
                latest.session.codec,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </div>
        <div className={styles.actions}>
          <div className={styles.segments} role="group" aria-label={t("dev.window")}>
            {WINDOWS.map((seconds) => (
              <button
                key={seconds}
                type="button"
                className={styles.segment}
                aria-pressed={seconds === windowSeconds}
                onClick={() => {
                  setWindowSeconds(seconds);
                }}
              >
                {t("dev.window_seconds", { seconds: String(seconds) })}
              </button>
            ))}
          </div>
          <button
            type="button"
            className={styles.action}
            aria-pressed={paused !== null}
            onClick={() => {
              setPaused(paused ? null : live.samples);
            }}
          >
            {t(paused ? "dev.resume_charts" : "dev.pause_charts")}
          </button>
          <button
            type="button"
            className={styles.action}
            onClick={() => {
              downloadText(CSV_NAME, metricsCsv(live.samples));
            }}
          >
            {t("dev.export_csv")}
          </button>
        </div>
      </header>
      {latest && <HealthTiles metrics={latest} samples={shown} formatFps={formatFps} lost={packetsLostIn(shown)} />}
      <FramePath stages={stageMedians(latest)} streamingApps={latest?.virtualCamera.streamingApps ?? null} />
      <div className={styles.grid}>
        <section className={styles.previewArea}>
          <h2 className={styles.chartTitle}>{t("dev.preview")}</h2>
          {status && mode && (
            <PreviewPanel
              mode={mode}
              previewOn
              attachPreview={preview.attach}
              previewShowing={preview.showing}
              frozenSince={null}
              onUnfreeze={() => {
                consoleData.changeControls({ frozen: false });
              }}
              onCameraOn={() => {
                consoleData.changeControls({ cameraOff: false });
              }}
            />
          )}
          {status?.session?.state === "live" && (
            <PreviewControls controls={status.controls} status={status} onChange={consoleData.changeControls} />
          )}
        </section>
        <LineChart
          title={t("dev.chart_fps")}
          series={[
            { label: t("dev.series_phone"), values: charts.phoneFps, tone: "primary" },
            { label: t("dev.series_camera"), values: charts.deliveredFps, tone: "secondary" },
          ]}
          max={niceCeiling(Math.max(MIN_FPS_SCALE, formatFps))}
          reference={{ label: String(formatFps), value: formatFps }}
          marks={charts.eventMarks}
          format={fps}
          startLabel={ago}
          endLabel={t("dev.now")}
        />
        <LineChart
          title={t("dev.chart_budget")}
          series={[]}
          bands={[
            { label: t("dev.stage_decode"), values: charts.decode, tone: "primary" },
            { label: t("dev.stage_color"), values: charts.color, tone: "secondary" },
            { label: t("dev.stage_deliver"), values: charts.deliver, tone: "tertiary" },
          ]}
          max={niceCeiling(latest?.budgetMs ?? 1)}
          reference={{ label: t("dev.series_budget"), value: latest?.budgetMs ?? 0 }}
          marks={charts.eventMarks}
          format={ms}
          startLabel={ago}
          endLabel={
            latest?.stages ? t("dev.headroom", { value: ms(latest.budgetMs - latest.stages.total.p95) }) : t("dev.now")
          }
        />
        <LineChart
          title={t("dev.chart_bitrate")}
          series={[{ label: t("dev.bitrate"), values: charts.bitrate, tone: "primary" }]}
          max={niceCeiling((latest?.ceilingKbps ?? KILOBITS_PER_MEGABIT) / KILOBITS_PER_MEGABIT)}
          reference={{ label: t("dev.series_ceiling"), value: (latest?.ceilingKbps ?? 0) / KILOBITS_PER_MEGABIT }}
          marks={charts.eventMarks}
          format={mbps}
          startLabel={ago}
          endLabel={t("dev.now")}
        />
        <LineChart
          title={t("dev.chart_network")}
          series={[
            { label: t("dev.series_round_trip"), values: charts.roundTrip, tone: "primary" },
            { label: t("dev.series_jitter"), values: charts.jitter, tone: "secondary" },
          ]}
          max={niceCeiling(Math.max(1, ...charts.roundTrip.map((value) => value ?? 0)))}
          marks={[...charts.eventMarks, ...charts.lossMarks]}
          markLegend={[{ label: t("dev.series_loss"), kind: "loss" }]}
          format={ms}
          startLabel={ago}
          endLabel={t("dev.now")}
        />
      </div>
      <div className={styles.bottom}>
        <FrameHistogram
          frameTimes={frameTimes}
          budgetMs={latest?.budgetMs ?? null}
          median={percentile(frameTimes, MEDIAN)}
          p95={percentile(frameTimes, P95)}
        />
        <DetailList
          title={t("dev.virtual_camera")}
          rows={[
            [t("dev.format_advertised"), latest?.virtualCamera.format ?? null],
            [t("dev.format_pending"), latest?.virtualCamera.pendingFormat ?? null],
            [t("dev.apps_using"), latest?.virtualCamera.streamingApps?.toString() ?? null],
            [t("dev.frames_delivered"), latest?.delivered?.frames.toString() ?? null],
            [t("dev.frames_dropped"), latest?.delivered?.dropped.toString() ?? null],
          ]}
        />
        <DetailList title={t("dev.phone")} rows={phoneRows(latest, shown)} />
        <EventList events={live.events} />
      </div>
      <p className={styles.note}>{t("dev.collect_note")}</p>
    </main>
  );
}

function phoneRows(latest: DevMetrics | undefined, samples: readonly DevMetrics[]): [string, string | null][] {
  const outbound = latest?.phone?.outbound ?? null;
  const interval = keyFrameIntervalSeconds(samples);
  const delivered =
    outbound?.frameWidth && outbound.frameHeight
      ? t("dev.size_at_fps", {
          width: String(outbound.frameWidth),
          height: String(outbound.frameHeight),
          fps: String(Math.round(outbound.framesPerSecond ?? 0)),
        })
      : null;
  return [
    [t("dev.requested"), latest?.session?.format ?? null],
    [t("dev.delivered"), delivered],
    [t("dev.camera"), latest?.session?.facing ? t(CAMERA_KEYS[latest.session.facing]) : null],
    [t("dev.quality_limitation"), outbound?.qualityLimitationReason ?? null],
    [t("dev.keyframe_interval"), interval === null ? null : t("dev.key_frames_every", { value: interval.toFixed(1) })],
  ];
}
