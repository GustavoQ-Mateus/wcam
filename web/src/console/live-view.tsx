import { useState } from "react";
import type { ControlsPatch, Status } from "../data/contract";
import { currentFacing, problemKey, signalPath, type ConsoleMode } from "../data/console-view";
import { LANGUAGE } from "../data/language";
import { useFrozenSince } from "../data/use-frozen-since";
import type { VideoFormat } from "../data/video-format";
import { usePreview } from "../media/use-preview";
import { ControlBar } from "./control-bar";
import { DetailsPanel } from "./details-panel";
import { FormatPanel } from "./format-panel";
import styles from "./live-view.module.scss";
import { PhonePanel } from "./phone-panel";
import { PreviewPanel } from "./preview-panel";
import { SignalPath } from "./signal-path";

interface LiveViewProps {
  status: Status;
  receivedAt: number;
  mode: ConsoleMode;
  onChange: (patch: ControlsPatch) => void;
  onDisconnect: () => void;
  onChooseFormat: (format: VideoFormat) => void;
  onCompare?: (() => void) | undefined;
  onUseVideo: () => void;
}

export function LiveView({
  status,
  receivedAt,
  mode,
  onChange,
  onDisconnect,
  onChooseFormat,
  onCompare,
  onUseVideo,
}: LiveViewProps) {
  const [previewOn, setPreviewOn] = useState(true);
  const preview = usePreview(previewOn);
  const frozenSince = useFrozenSince(mode === "frozen", receivedAt, LANGUAGE);
  const facing = currentFacing(status);
  const { session, controls } = status;
  return (
    <div className={styles.layout}>
      <section className={styles.main}>
        <PreviewPanel
          mode={mode}
          previewOn={previewOn}
          attachPreview={preview.attach}
          previewState={preview.state}
          frozenSince={frozenSince}
          onShowPreviewAgain={preview.showAgain}
        />
        <ControlBar
          controls={controls}
          facing={facing}
          previewOn={previewOn}
          previewStopped={previewOn && preview.state === "stopped"}
          onChange={onChange}
          onTogglePreview={() => {
            setPreviewOn((on) => !on);
          }}
          onDisconnect={onDisconnect}
          onCompare={onCompare}
          onUseVideo={onUseVideo}
        />
      </section>
      <aside className={styles.aside}>
        {session && (
          <PhonePanel
            session={session}
            facing={facing}
            onChooseFacing={(next) => {
              onChange({ facing: next });
            }}
          />
        )}
        <SignalPath steps={signalPath(status)} problemKey={problemKey(status)} />
        <FormatPanel videoFormat={status.videoFormat} onChoose={onChooseFormat} />
        <DetailsPanel status={status} />
      </aside>
    </div>
  );
}
