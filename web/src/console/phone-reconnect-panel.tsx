import type { Session } from "../data/contract";
import { secondsUntil, svgDataUrl } from "../data/console-format";
import { t } from "../data/language";
import { ConsoleButton } from "./console-button";
import styles from "./phone-reconnect-panel.module.scss";

interface PhoneReconnectPanelProps {
  session: Session | null;
  qrSvg: string | null;
  expiresAt: string | null;
  receivedAt: number;
  onNewPairing: () => void;
  onConfirm: () => void;
  onReject: () => void;
}

export function PhoneReconnectPanel({
  session,
  qrSvg,
  expiresAt,
  receivedAt,
  onNewPairing,
  onConfirm,
  onReject,
}: PhoneReconnectPanelProps) {
  const title = t("console.pairing_title");
  if (session?.state === "awaiting_confirmation") {
    return (
      <section className={styles.panel}>
        <h2 className={styles.title}>{t("console.confirm_title")}</h2>
        <p className={styles.code}>{session.confirmationCode}</p>
        {!session.confirmations.pc && (
          <div className={styles.actions}>
            <ConsoleButton variant="primary" onClick={onConfirm}>
              {t("console.confirm")}
            </ConsoleButton>
            <ConsoleButton variant="secondary" onClick={onReject}>
              {t("console.reject")}
            </ConsoleButton>
          </div>
        )}
      </section>
    );
  }
  if (session) {
    return (
      <section className={styles.panel}>
        <h2 className={styles.title}>{t("console.state_connecting")}</h2>
        <p className={styles.note}>{session.deviceName ?? t("console.device_unknown")}</p>
      </section>
    );
  }
  const showQr = qrSvg !== null && expiresAt !== null;
  return (
    <section className={styles.panel}>
      <h2 className={styles.title}>{title}</h2>
      {showQr && (
        <div className={styles.qrFrame}>
          <img className={styles.qr} src={svgDataUrl(qrSvg)} alt={title} />
        </div>
      )}
      {showQr && (
        <p className={styles.note}>
          {t("console.pairing_expires", { seconds: String(secondsUntil(expiresAt, receivedAt)) })}
        </p>
      )}
      <div>
        <ConsoleButton variant={showQr ? "secondary" : "primary"} onClick={onNewPairing}>
          {t("console.pairing_new")}
        </ConsoleButton>
      </div>
    </section>
  );
}
