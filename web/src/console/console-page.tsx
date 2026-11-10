import { comparisonAvailable } from "../data/console-format";
import { errorMessageKey } from "../data/i18n";
import { t } from "../data/language";
import { useConsole } from "../data/use-console";
import { useHealth, type HealthState } from "../data/use-health";
import styles from "./console-page.module.scss";
import { ComparisonPanel } from "./comparison-panel";
import { PairingPanel } from "./pairing-panel";
import { QualityPanel } from "./quality-panel";
import { SessionPanel } from "./session-panel";
import { useComparison } from "./use-comparison";
import { VirtualCameraPanel } from "./virtual-camera-panel";

export default function ConsolePage() {
  const health = useHealth();
  const data = useConsole();
  const session = data.status?.session ?? null;
  const comparison = useComparison();
  const canCompare = comparisonAvailable(data.status);
  return (
    <main className={styles.page}>
      <h1 className={styles.name}>{t("app.name")}</h1>
      <p className={styles.status} data-state={health.kind} role="status">
        <span className={styles.indicator} aria-hidden="true" />
        {statusText(health)}
      </p>
      {data.status && <VirtualCameraPanel virtualCamera={data.status.virtualCamera} process={data.status.process} />}
      {session ? (
        <SessionPanel
          session={session}
          onConfirm={data.confirm}
          onReject={data.reject}
          onDisconnect={data.disconnect}
          onCompare={canCompare ? comparison.capture : undefined}
        />
      ) : (
        <PairingPanel
          qrSvg={data.qrSvg}
          expiresAt={data.status?.pairing?.expiresAt ?? null}
          receivedAt={data.receivedAt}
          onNewPairing={data.newPairing}
        />
      )}
      {data.status?.devTools && <ComparisonPanel view={comparison.view} onAddScreen={comparison.addScreen} />}
      {data.status && <QualityPanel preset={data.status.qualityPreset} onChoose={data.chooseQualityPreset} />}
      {data.errorCode && (
        <p className={styles.error} role="alert">
          {t(errorMessageKey(data.errorCode))}
        </p>
      )}
    </main>
  );
}

function statusText(health: HealthState): string {
  switch (health.kind) {
    case "checking":
      return t("console.status_checking");
    case "running":
      return t("console.status_running", { version: health.version });
    case "failed":
      return t(errorMessageKey(health.code));
  }
}
