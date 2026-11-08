import type { Session } from "../data/contract";
import { colorCalibrationKey, videoFormatValues } from "../data/console-format";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import { ConsoleButton } from "./console-button";
import styles from "./session-panel.module.scss";

interface SessionPanelProps {
  session: Session;
  onConfirm: () => void;
  onReject: () => void;
  onDisconnect: () => void;
  onCompare?: (() => void) | undefined;
}

const CODE_SEPARATOR = "-";
const TITLE_KEYS: Readonly<Record<Session["state"], MessageKey>> = {
  connecting: "console.state_connecting",
  awaiting_confirmation: "console.confirm_title",
  live: "console.state_live",
};

export function SessionPanel({ session, onConfirm, onReject, onDisconnect, onCompare }: SessionPanelProps) {
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
      {awaiting && session.confirmationCode && (
        <p className={styles.code}>
          <span className="visually-hidden">{session.confirmationCode}</span>
          {session.confirmationCode.split(CODE_SEPARATOR).map((group, index) => (
            <span key={index} aria-hidden="true">
              {group}
            </span>
          ))}
        </p>
      )}
      {session.video && (
        <p className={styles.video}>
          <span>{t("console.video_format", videoFormatValues(session.video))}</span>
          <span>{session.video.codec}</span>
        </p>
      )}
      {session.video && <p className={styles.color}>{t(colorCalibrationKey(session.video.colorCalibration))}</p>}
      {session.video && session.video.framesScaled > 0 && (
        <p className={styles.warning}>
          <span className={styles.warningMark} aria-hidden="true" />
          {t("console.frames_scaled", { count: String(session.video.framesScaled) })}
        </p>
      )}
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
          <>
            <ConsoleButton variant="secondary" onClick={onDisconnect}>
              {t("console.disconnect")}
            </ConsoleButton>
            {onCompare && (
              <ConsoleButton variant="secondary" onClick={onCompare}>
                {t("console.dev_compare")}
              </ConsoleButton>
            )}
          </>
        )}
      </div>
    </section>
  );
}
