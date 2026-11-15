import { cpuPercentValue } from "../data/console-format";
import type { LibraryVideo, Status } from "../data/contract";
import { formatName } from "../data/format-name";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import { clipAtTime } from "../data/timeline";
import styles from "./side-panel.module.scss";

interface DetailsPanelProps {
  status: Status;
}

interface DetailRow {
  labelKey: MessageKey;
  value: string | null;
}

const FPS_DECIMALS = 1;
const BITRATE_DECIMALS = 1;
const KILOBITS_PER_MEGABIT = 1000;

export function DetailsPanel({ status }: DetailsPanelProps) {
  return (
    <details className={styles.panel}>
      <summary className={styles.summary}>{t("console.details")}</summary>
      <dl className={styles.details}>
        {detailRows(status).map((row) => (
          <div key={row.labelKey} className={styles.detail}>
            <dt className={styles.detailLabel}>{t(row.labelKey)}</dt>
            <dd className={styles.detailValue} data-empty={row.value === null}>
              {row.value ?? t("console.detail_none")}
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function detailRows(status: Status): DetailRow[] {
  const { videoFormat, process } = status;
  return [
    ...sourceRows(status),
    { labelKey: "console.detail_camera_format", value: formatName(videoFormat.camera) },
    {
      labelKey: "console.detail_cpu",
      value: t("console.detail_percent", { percent: cpuPercentValue(process.cpuPercent) }),
    },
  ];
}

function sourceRows(status: Status): DetailRow[] {
  const { session, videoSource } = status;
  const playing = videoSource.active ? playingVideo(status) : null;
  if (playing) {
    return videoFileRows(playing);
  }
  const video = session?.video ?? null;
  return [
    { labelKey: "console.detail_resolution", value: video && `${String(video.width)} × ${String(video.height)}` },
    { labelKey: "console.detail_fps", value: video && video.fps.toFixed(FPS_DECIMALS) },
    {
      labelKey: "console.detail_bitrate",
      value:
        video &&
        t("console.detail_bitrate_value", {
          mbps: (video.bitrateKbps / KILOBITS_PER_MEGABIT).toFixed(BITRATE_DECIMALS),
        }),
    },
    { labelKey: "console.detail_codec", value: video && video.codec },
  ];
}

function playingVideo({ videoSource }: Status): LibraryVideo | null {
  const { clips } = videoSource.timeline;
  const place = clipAtTime(clips, videoSource.positionSeconds ?? 0);
  const clip = clips[place?.index ?? 0];
  return videoSource.videos.find((video) => video.id === clip?.videoId) ?? null;
}

function videoFileRows(file: LibraryVideo): DetailRow[] {
  return [
    { labelKey: "console.detail_resolution", value: `${String(file.width)} × ${String(file.height)}` },
    { labelKey: "console.detail_fps", value: file.fps.toFixed(FPS_DECIMALS) },
    { labelKey: "console.detail_codec", value: file.codec },
  ];
}
