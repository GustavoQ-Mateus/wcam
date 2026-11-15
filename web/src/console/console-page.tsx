import { useState } from "react";
import { comparisonAvailable } from "../data/console-format";
import { consoleMode, isLiveMode, phoneFlowMode, stateBadge } from "../data/console-view";
import type { TimelineClip } from "../data/contract";
import { errorMessageKey } from "../data/i18n";
import { t } from "../data/language";
import { useConsole } from "../data/use-console";
import { useVideoSource } from "../data/use-video-source";
import { ComparisonPanel } from "./comparison-panel";
import { ConfirmView } from "./confirm-view";
import { ConnectingView } from "./connecting-view";
import { ConsoleHeader } from "./console-header";
import styles from "./console-page.module.scss";
import { LiveView } from "./live-view";
import { useComparison } from "./use-comparison";
import { VideoEditor } from "./video-editor";
import { WaitingView } from "./waiting-view";

const NO_CLIPS: readonly TimelineClip[] = [];

export default function ConsolePage() {
  const data = useConsole();
  const comparison = useComparison();
  const { status } = data;
  const video = useVideoSource(status?.videoSource.timeline.clips ?? NO_CLIPS);
  const [editorFor, setEditorFor] = useState<string | null>(null);
  const [seenActive, setSeenActive] = useState(false);
  const active = status?.videoSource.active ?? false;
  if (active !== seenActive) {
    setSeenActive(active);
    if (!active) {
      setEditorFor(null);
    }
  }
  const session = status?.session ?? null;
  const mode = status ? consoleMode(status) : null;
  const editing = active || (session?.state === "live" && editorFor === session.id);
  const flowMode = status && (editing ? phoneFlowMode(status) : mode);
  return (
    <main className={styles.page}>
      <ConsoleHeader badge={status ? stateBadge(status) : null} />
      {data.errorCode && (
        <p className={styles.error} role="alert">
          {t(errorMessageKey(data.errorCode))}
        </p>
      )}
      {status && mode && editing && (
        <VideoEditor
          status={status}
          receivedAt={data.receivedAt}
          mode={mode}
          video={video}
          onChange={data.changeControls}
          onChooseFormat={data.chooseVideoFormat}
          onClose={() => {
            setEditorFor(null);
          }}
        />
      )}
      {status && flowMode === "waiting" && (
        <WaitingView
          qrSvg={data.qrSvg}
          expiresAt={status.pairing?.expiresAt ?? null}
          receivedAt={data.receivedAt}
          onNewPairing={data.newPairing}
        />
      )}
      {session && flowMode === "connecting" && <ConnectingView session={session} />}
      {session && flowMode === "confirming" && (
        <ConfirmView session={session} onConfirm={data.confirm} onReject={data.reject} />
      )}
      {status && mode && !editing && isLiveMode(mode) && (
        <LiveView
          status={status}
          receivedAt={data.receivedAt}
          mode={mode}
          onChange={data.changeControls}
          onDisconnect={data.disconnect}
          onChooseFormat={data.chooseVideoFormat}
          onCompare={comparisonAvailable(status) ? comparison.capture : undefined}
          onUseVideo={() => {
            setEditorFor(session?.id ?? null);
          }}
        />
      )}
      {status?.devTools && <ComparisonPanel view={comparison.view} onAddScreen={comparison.addScreen} />}
    </main>
  );
}
