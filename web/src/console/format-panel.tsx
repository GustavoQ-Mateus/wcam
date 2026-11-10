import { useId } from "react";
import type { VideoFormatStatus } from "../data/contract";
import { formatName } from "../data/format-name";
import { formatView, type FormatOption } from "../data/format-view";
import { t } from "../data/language";
import { useFormatChoice } from "../data/use-format-choice";
import {
  frameRateHintKey,
  frameRateKey,
  maxBitrateMbps,
  resolutionKey,
  type FrameRate,
  type Resolution,
  type VideoFormat,
} from "../data/video-format";
import styles from "./format-panel.module.scss";

interface FormatPanelProps {
  videoFormat: VideoFormatStatus;
  onChoose: (format: VideoFormat) => void;
}

export function FormatPanel({ videoFormat, onChoose }: FormatPanelProps) {
  const titleId = useId();
  const resolutionId = useId();
  const frameRateId = useId();
  const choice = useFormatChoice(videoFormat.selected, onChoose);
  const view = formatView(videoFormat.selected, videoFormat.available, choice.pending);
  return (
    <section className={styles.panel} aria-labelledby={titleId}>
      <h2 id={titleId} className={styles.title}>
        {formatName(videoFormat.selected)}
      </h2>
      {videoFormat.pending && (
        <p className={styles.pending}>
          <span className={styles.warningMark} aria-hidden="true" />
          {t("console.format_pending")}
        </p>
      )}
      {(view.resolutions.length > 0 || view.frameRates.length > 0) && (
        <div className={styles.choices}>
          {view.resolutions.length > 0 && (
            <>
              <p id={resolutionId} className={styles.label}>
                {t("format.resolution_label")}
              </p>
              <Segments
                labelledBy={resolutionId}
                options={view.resolutions}
                name={(value: Resolution) => t(resolutionKey(value))}
                onChoose={choice.choose}
              />
            </>
          )}
          {view.frameRates.length > 0 && (
            <>
              <p id={frameRateId} className={styles.label}>
                {t("format.frame_rate_label")}
              </p>
              <div className={styles.control}>
                <Segments
                  labelledBy={frameRateId}
                  options={view.frameRates}
                  name={(value: FrameRate) => t(frameRateKey(value))}
                  onChoose={choice.choose}
                />
                <p className={styles.hint}>{t(frameRateHintKey(view.frameRate))}</p>
              </div>
            </>
          )}
        </div>
      )}
      <p className={styles.detail}>
        {t("format.bitrate_limit", { mbps: String(maxBitrateMbps(videoFormat.selected)) })}
      </p>
    </section>
  );
}

interface SegmentsProps<T extends string | number> {
  labelledBy: string;
  options: FormatOption<T>[];
  name: (value: T) => string;
  onChoose: (format: VideoFormat) => void;
}

function Segments<T extends string | number>({ labelledBy, options, name, onChoose }: SegmentsProps<T>) {
  return (
    <div
      className={styles.track}
      role="radiogroup"
      aria-labelledby={labelledBy}
      style={{ gridTemplateColumns: `repeat(${String(options.length)}, minmax(0, 1fr))` }}
    >
      {options.map((option) => (
        <label key={option.value} className={styles.segment} data-checked={option.checked}>
          <input
            type="radio"
            className="visually-hidden"
            name={labelledBy}
            checked={option.checked}
            onChange={() => {
              onChoose(option.format);
            }}
          />
          {option.pending && <span className={styles.pendingMark} aria-hidden="true" />}
          {name(option.value)}
        </label>
      ))}
    </div>
  );
}
