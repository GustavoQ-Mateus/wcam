import type { Session } from "../data/contract";
import { videoFormatValues } from "../data/console-format";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import { ConsoleButton } from "./console-button";
import styles from "./session-panel.module.scss";

interface SessionPanelProps {
  session: Session;
  onConfirm: () => void;
  onReject: () => void;
  onDisconnect: () => void;
}

const TITLE_KEYS: Readonly<Record<Session["state"], MessageKey>> = {
  connecting: "console.state_connecting",
  awaiting_confirmation: "console.confirm_title",
  live: "console.state_live",
};

export function SessionPanel({ session, onConfirm, onReject, onDisconnect }: SessionPanelProps) {
  const awaiting = session.state === "awaiting_confirmation";
  return (
    <section className={styles.panel} data-state={session.state}>
      <h2 className={styles.title}>
        <span className={styles.indicator} aria-hidden="true" />
        {t(TITLE_KEYS[session.state])}
      </h2>
      <p className={styles.device}>
        <span>{session.deviceName ?? t("console.device_unknown")}</span>
        <span>{session.remoteIp}</span>
      </p>
      {awaiting && session.confirmationCode && <p className={styles.code}>{session.confirmationCode}</p>}
      {session.video && <p className={styles.video}>{t("console.video_format", videoFormatValues(session.video))}</p>}
      <div className={styles.actions}>
        {awaiting ? (
          <>
            <ConsoleButton variant="primary" onClick={onConfirm}>
              {t("console.confirm")}
            </ConsoleButton>
            <ConsoleButton variant="secondary" onClick={onReject}>
              {t("console.reject")}
            </ConsoleButton>
          </>
        ) : (
          <ConsoleButton variant="secondary" onClick={onDisconnect}>
            {t("console.disconnect")}
          </ConsoleButton>
        )}
      </div>
    </section>
  );
}
