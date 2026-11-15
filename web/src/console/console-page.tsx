import { comparisonAvailable } from "../data/console-format";
import { consoleMode, isLiveMode, stateBadge } from "../data/console-view";
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
import { VideoPanel } from "./video-panel";
import { VideoView } from "./video-view";
import { WaitingView } from "./waiting-view";

export default function ConsolePage() {
  const data = useConsole();
  const comparison = useComparison();
  const video = useVideoSource();
  const { status } = data;
  const mode = status ? consoleMode(status) : null;
  const videoFile = status?.videoSource.active ? status.videoSource.file : null;
  const videoPanel = status && <VideoPanel videoSource={status.videoSource} actions={video} />;
  return (
    <main className={styles.page}>
      <ConsoleHeader badge={status ? stateBadge(status) : null} />
      {data.errorCode && (
        <p className={styles.error} role="alert">
          {t(errorMessageKey(data.errorCode))}
        </p>
      )}
      {status && mode && videoFile && (
        <VideoView
          status={status}
          file={videoFile}
          receivedAt={data.receivedAt}
          mode={mode}
          video={video}
          onChange={data.changeControls}
          onChooseFormat={data.chooseVideoFormat}
        />
      )}
      {status && mode === "waiting" && (
        <WaitingView
          qrSvg={data.qrSvg}
          expiresAt={status.pairing?.expiresAt ?? null}
          receivedAt={data.receivedAt}
          onNewPairing={data.newPairing}
          videoPanel={videoPanel}
        />
      )}
      {status?.session && mode === "connecting" && <ConnectingView session={status.session} />}
      {status?.session && mode === "confirming" && (
        <ConfirmView session={status.session} onConfirm={data.confirm} onReject={data.reject} />
      )}
      {status && mode && !videoFile && isLiveMode(mode) && (
        <LiveView
          status={status}
          receivedAt={data.receivedAt}
          mode={mode}
          onChange={data.changeControls}
          onDisconnect={data.disconnect}
          onChooseFormat={data.chooseVideoFormat}
          onCompare={comparisonAvailable(status) ? comparison.capture : undefined}
          videoPanel={videoPanel}
        />
      )}
      {status?.devTools && <ComparisonPanel view={comparison.view} onAddScreen={comparison.addScreen} />}
    </main>
  );
}
