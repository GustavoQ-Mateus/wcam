import type { Session } from "../data/contract";
import { t } from "../data/language";
import styles from "./confirm-view.module.scss";

interface ConnectingViewProps {
  session: Session;
}

export function ConnectingView({ session }: ConnectingViewProps) {
  return (
    <section className={styles.view}>
      <p className={styles.device}>
        {session.deviceName ?? t("console.device_unknown")} · {session.remoteIp}
      </p>
      <h2 className={styles.title}>{t("console.state_connecting")}</h2>
    </section>
  );
}
