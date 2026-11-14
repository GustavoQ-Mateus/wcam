import type { Session } from "../data/contract";
import { t } from "../data/language";
import { ConsoleButton } from "./console-button";
import styles from "./confirm-view.module.scss";
import { StatusMark } from "./status-mark";

interface ConfirmViewProps {
  session: Session;
  onConfirm: () => void;
  onReject: () => void;
}

const CODE_SEPARATOR = "-";

export function ConfirmView({ session, onConfirm, onReject }: ConfirmViewProps) {
  const code = session.confirmationCode ?? "";
  const { pc, phone } = session.confirmations;
  return (
    <section className={styles.view}>
      <p className={styles.device}>
        {session.deviceName ?? t("console.device_unknown")} · {session.remoteIp}
      </p>
      <h2 className={styles.title}>{t("console.confirm_title")}</h2>
      <p className={styles.code}>
        <span className="visually-hidden">{code}</span>
        {code.split(CODE_SEPARATOR).map((group, groupIndex) => (
          <span key={groupIndex} className={styles.group} aria-hidden="true">
            {[...group].map((character, index) => (
              <span key={index} className={styles.cell}>
                {character}
              </span>
            ))}
          </span>
        ))}
      </p>
      <ul className={styles.sides}>
        <ConfirmationSide labelKey="console.confirmation_pc" done={pc} />
        <ConfirmationSide labelKey="console.confirmation_phone" done={phone} />
      </ul>
      {!pc && (
        <div className={styles.actions}>
          <ConsoleButton variant="primary" onClick={onConfirm}>
            {t("console.confirm")}
          </ConsoleButton>
          <ConsoleButton variant="secondary" onClick={onReject}>
            {t("console.reject")}
          </ConsoleButton>
        </div>
      )}
      <p className={styles.hint}>{t("console.confirm_hint")}</p>
    </section>
  );
}

interface ConfirmationSideProps {
  labelKey: "console.confirmation_pc" | "console.confirmation_phone";
  done: boolean;
}

function ConfirmationSide({ labelKey, done }: ConfirmationSideProps) {
  return (
    <li className={styles.side} data-done={done}>
      <StatusMark shape={done ? "dot" : "ring"} tone={done ? "live" : "neutral"} />
      {t(labelKey)}
      <span className={styles.sideState}>{t(done ? "console.confirmation_done" : "console.confirmation_waiting")}</span>
    </li>
  );
}
