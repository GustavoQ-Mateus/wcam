import { secondsUntil, svgDataUrl, windowProgress } from "../data/console-format";
import { t } from "../data/language";
import { ConsoleButton } from "./console-button";
import styles from "./waiting-view.module.scss";

interface WaitingViewProps {
  qrSvg: string | null;
  expiresAt: string | null;
  receivedAt: number;
  onNewPairing: () => void;
}

export function WaitingView({ qrSvg, expiresAt, receivedAt, onNewPairing }: WaitingViewProps) {
  const title = t("console.pairing_title");
  const showQr = qrSvg !== null && expiresAt !== null;
  return (
    <section className={styles.view}>
      <div className={styles.qrFrame} data-empty={!showQr}>
        {showQr && <img className={styles.qr} src={svgDataUrl(qrSvg)} alt={title} />}
      </div>
      <div className={styles.intro}>
        <h2 className={styles.title}>{title}</h2>
        <ol className={styles.steps}>
          <li>{t("console.step_same_wifi")}</li>
          <li>{t("console.step_certificate")}</li>
          <li>{t("console.step_code")}</li>
        </ol>
        {showQr && (
          <div className={styles.countdown}>
            <p>{t("console.pairing_expires", { seconds: String(secondsUntil(expiresAt, receivedAt)) })}</p>
            <div className={styles.track}>
              <div
                className={styles.fill}
                style={{ inlineSize: `${String(windowProgress(expiresAt, receivedAt))}%` }}
              />
            </div>
          </div>
        )}
        <div>
          <ConsoleButton variant={showQr ? "secondary" : "primary"} onClick={onNewPairing}>
            {t("console.pairing_new")}
          </ConsoleButton>
        </div>
      </div>
    </section>
  );
}
