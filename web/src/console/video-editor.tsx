import { useState, type KeyboardEvent } from "react";
import type { ControlsPatch, Status, TimelineClip } from "../data/contract";
import type { ConsoleMode } from "../data/console-view";
import { currentFacing } from "../data/console-view";
import { errorMessageKey } from "../data/i18n";
import { LANGUAGE, t } from "../data/language";
import { deleteClip, insertVideo, moveClip, splitAt, timelineLength } from "../data/timeline";
import { useFrozenSince } from "../data/use-frozen-since";
import { usePlaybackPosition } from "../data/use-playback-position";
import type { VideoSourceActions } from "../data/use-video-source";
import type { VideoFormat } from "../data/video-format";
import { KEYBOARD_STEP_SECONDS } from "../data/video-position";
import { usePreview } from "../media/use-preview";
import { DetailsPanel } from "./details-panel";
import { EditorTimeline } from "./editor-timeline";
import { FormatPanel } from "./format-panel";
import { PhonePanel } from "./phone-panel";
import { PreviewPanel } from "./preview-panel";
import { TransportBar } from "./transport-bar";
import styles from "./video-editor.module.scss";
import { VideoLibrary } from "./video-library";

type KeyCommand = "pause" | "split" | "delete" | "start";

const ZOOM_LEVELS = [1, 2, 4, 8, 16, 32];
const KEY_COMMANDS: Readonly<Record<string, KeyCommand>> = {
  " ": "pause",
  s: "split",
  S: "split",
  Delete: "delete",
  Backspace: "delete",
  Home: "start",
};

interface VideoEditorProps {
  status: Status;
  receivedAt: number;
  mode: ConsoleMode;
  video: VideoSourceActions;
  onChange: (patch: ControlsPatch) => void;
  onChooseFormat: (format: VideoFormat) => void;
  onClose: () => void;
}

export function VideoEditor({ status, receivedAt, mode, video, onChange, onChooseFormat, onClose }: VideoEditorProps) {
  const [previewOn, setPreviewOn] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoomIndex, setZoomIndex] = useState(0);
  const preview = usePreview(previewOn);
  const { controls, videoSource, session } = status;
  const { active } = videoSource;
  const frozen = active && controls.frozen;
  const frozenSince = useFrozenSince(mode === "frozen", receivedAt, LANGUAGE);
  const clips = video.clips;
  const duration = timelineLength(clips);
  const playback = usePlaybackPosition({
    active,
    running: !frozen,
    positionSeconds: videoSource.positionSeconds,
    receivedAt,
    duration,
    onSeek: video.seek,
  });
  const phoneLive = session?.state === "live";
  const selectedIndex = clips.findIndex((clip) => clip.id === selectedId);
  const now = () => playback.positionAt(Date.now());

  const insertAt = (videoId: string, index: number) => {
    const chosen = videoSource.videos.find((item) => item.id === videoId);
    if (chosen) {
      video.changeClips(insertVideo(clips, chosen, index, crypto.randomUUID()));
    }
  };
  const split = () => {
    const next = splitAt(clips, now(), crypto.randomUUID());
    if (next.length > clips.length) {
      video.changeClips(next);
    }
  };
  const removeSelected = () => {
    if (selectedIndex !== -1) {
      video.changeClips(deleteClip(clips, selectedIndex));
      setSelectedId(null);
    }
  };
  const moveSelected = (direction: 1 | -1) => {
    if (selectedIndex !== -1) {
      changeIfMoved(clips, moveClip(clips, selectedIndex, selectedIndex + direction), video.changeClips);
    }
  };
  const togglePause = () => {
    onChange({ frozen: !controls.frozen });
  };
  const handleKey = (event: KeyboardEvent<HTMLDivElement>) => {
    const direction = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (direction !== 0 && event.altKey) {
      event.preventDefault();
      moveSelected(direction);
      return;
    }
    if (direction !== 0) {
      event.preventDefault();
      playback.seek(now() + direction * KEYBOARD_STEP_SECONDS);
      return;
    }
    const command = KEY_COMMANDS[event.key];
    if (!command) {
      return;
    }
    event.preventDefault();
    const actions = {
      pause: active ? togglePause : noop,
      split,
      delete: removeSelected,
      start: () => playback.seek(0),
    };
    actions[command]();
  };

  return (
    <div className={styles.editor}>
      <div className={styles.top}>
        <section className={styles.main}>
          <PreviewPanel
            mode={mode}
            previewOn={previewOn}
            attachPreview={preview.attach}
            previewState={preview.state}
            frozenSince={frozenSince}
            onShowPreviewAgain={preview.showAgain}
          />
          {active && <p className={styles.state}>{t("console.video_not_live")}</p>}
        </section>
        <aside className={styles.aside}>
          <VideoLibrary
            videos={videoSource.videos}
            clips={clips}
            uploads={video.uploads}
            canSend={phoneLive}
            onAddFiles={video.addFiles}
            onDismissUpload={video.dismissUpload}
            onAddToTimeline={(videoId) => {
              insertAt(videoId, clips.length);
            }}
            onRemove={video.remove}
          />
          {session && phoneLive && (
            <PhonePanel
              session={session}
              facing={currentFacing(status)}
              cameraInUse={!active}
              onChooseFacing={(facing) => {
                onChange({ facing });
              }}
            />
          )}
        </aside>
      </div>
      <TransportBar
        active={active}
        frozen={controls.frozen}
        mirror={controls.mirror}
        duration={duration}
        positionAt={playback.positionAt}
        canUse={phoneLive && clips.length > 0}
        canSplit={clips.length > 0}
        canDelete={selectedIndex !== -1}
        canZoomIn={zoomIndex < ZOOM_LEVELS.length - 1}
        canZoomOut={zoomIndex > 0}
        previewOn={previewOn}
        previewStopped={previewOn && preview.state === "stopped"}
        onTogglePause={togglePause}
        onSplit={split}
        onDelete={removeSelected}
        onZoom={(direction) => {
          setZoomIndex((index) => Math.min(ZOOM_LEVELS.length - 1, Math.max(0, index + direction)));
        }}
        onMirror={() => {
          onChange({ mirror: !controls.mirror });
        }}
        onTogglePreview={() => {
          setPreviewOn((on) => !on);
        }}
        onUse={video.use}
        onBackToCamera={active ? video.backToCamera : onClose}
      />
      {video.errorCode && (
        <p className={styles.error} role="alert">
          {t(errorMessageKey(video.errorCode))}
        </p>
      )}
      <EditorTimeline
        videos={videoSource.videos}
        clips={clips}
        zoom={ZOOM_LEVELS[zoomIndex] ?? 1}
        selectedId={selectedId}
        positionAt={playback.positionAt}
        onSelect={setSelectedId}
        onSeek={playback.seek}
        onChange={video.changeClips}
        onInsertVideo={insertAt}
        onDropFiles={phoneLive ? video.addFiles : noop}
        onKeyDown={handleKey}
      />
      <div className={styles.bottom}>
        <FormatPanel videoFormat={status.videoFormat} onChoose={onChooseFormat} />
        <DetailsPanel status={status} />
      </div>
    </div>
  );
}

function changeIfMoved(
  before: readonly TimelineClip[],
  after: TimelineClip[],
  onChange: (clips: TimelineClip[]) => void,
): void {
  if (after.some((clip, index) => clip.id !== before[index]?.id)) {
    onChange(after);
  }
}

function noop(): void {}
