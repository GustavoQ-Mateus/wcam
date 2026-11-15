import { useState } from "react";
import type { ControlsPatch, Status, VideoFile } from "../data/contract";
import type { ConsoleMode } from "../data/console-view";
import { LANGUAGE } from "../data/language";
import { useFrozenSince } from "../data/use-frozen-since";
import type { VideoSourceActions } from "../data/use-video-source";
import type { VideoFormat } from "../data/video-format";
import { usePreview } from "../media/use-preview";
import { ControlBar } from "./control-bar";
import { DetailsPanel } from "./details-panel";
import { FormatPanel } from "./format-panel";
import styles from "./live-view.module.scss";
import { PreviewPanel } from "./preview-panel";
import { VideoPanel } from "./video-panel";
import { VideoTimeline } from "./video-timeline";

interface VideoViewProps {
  status: Status;
  file: VideoFile;
  receivedAt: number;
  mode: ConsoleMode;
  video: VideoSourceActions;
  onChange: (patch: ControlsPatch) => void;
  onChooseFormat: (format: VideoFormat) => void;
}

export function VideoView({ status, file, receivedAt, mode, video, onChange, onChooseFormat }: VideoViewProps) {
  const [previewOn, setPreviewOn] = useState(true);
  const preview = usePreview(previewOn);
  const frozen = mode === "frozen";
  const frozenSince = useFrozenSince(frozen, receivedAt, LANGUAGE);
  const { controls, videoSource } = status;
  return (
    <div className={styles.layout}>
      <section className={styles.main}>
        <PreviewPanel
          mode={mode}
          previewOn={previewOn}
          attachPreview={preview.attach}
          previewState={preview.state}
          frozenSince={frozenSince}
          onUnfreeze={() => {
            onChange({ frozen: false });
          }}
          onCameraOn={() => {
            onChange({ cameraOff: false });
          }}
          onShowPreviewAgain={preview.showAgain}
        />
        <VideoTimeline
          duration={file.durationSeconds}
          sample={{ seconds: videoSource.positionSeconds ?? 0, receivedAt }}
          running={!frozen}
          onSeek={video.seek}
        />
        <ControlBar
          controls={controls}
          facing={null}
          previewOn={previewOn}
          previewStopped={previewOn && preview.state === "stopped"}
          onChange={onChange}
          onTogglePreview={() => {
            setPreviewOn((on) => !on);
          }}
          onDisconnect={video.backToPhone}
          onBackToPhone={video.backToPhone}
        />
      </section>
      <aside className={styles.aside}>
        <VideoPanel videoSource={videoSource} actions={video} />
        <FormatPanel videoFormat={status.videoFormat} onChoose={onChooseFormat} />
        <DetailsPanel status={status} />
      </aside>
    </div>
  );
}
