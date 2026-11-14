import { comparisonAvailable } from "../data/console-format";
import { consoleMode, isLiveMode, stateBadge } from "../data/console-view";
import { errorMessageKey } from "../data/i18n";
import { t } from "../data/language";
import { useConsole } from "../data/use-console";
import { ComparisonPanel } from "./comparison-panel";
import { ConfirmView } from "./confirm-view";
import { ConnectingView } from "./connecting-view";
import { ConsoleHeader } from "./console-header";
import styles from "./console-page.module.scss";
import { LiveView } from "./live-view";
import { useComparison } from "./use-comparison";
import { WaitingView } from "./waiting-view";

export default function ConsolePage() {
  const data = useConsole();
  const comparison = useComparison();
  const { status } = data;
  const mode = status ? consoleMode(status) : null;
  return (
    <main className={styles.page}>
      <ConsoleHeader badge={status ? stateBadge(status) : null} />
      {data.errorCode && (
        <p className={styles.error} role="alert">
          {t(errorMessageKey(data.errorCode))}
        </p>
      )}
      {status && mode === "waiting" && (
        <WaitingView
          qrSvg={data.qrSvg}
          expiresAt={status.pairing?.expiresAt ?? null}
          receivedAt={data.receivedAt}
          onNewPairing={data.newPairing}
        />
      )}
      {status?.session && mode === "connecting" && <ConnectingView session={status.session} />}
      {status?.session && mode === "confirming" && (
        <ConfirmView session={status.session} onConfirm={data.confirm} onReject={data.reject} />
      )}
      {status && mode && isLiveMode(mode) && (
        <LiveView
          status={status}
          receivedAt={data.receivedAt}
          mode={mode}
          onChange={data.changeControls}
          onDisconnect={data.disconnect}
          onChooseFormat={data.chooseVideoFormat}
          onCompare={comparisonAvailable(status) ? comparison.capture : undefined}
        />
      )}
      {status?.devTools && <ComparisonPanel view={comparison.view} onAddScreen={comparison.addScreen} />}
    </main>
  );
}
