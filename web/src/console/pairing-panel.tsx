import { secondsUntil, svgDataUrl } from "../data/console-format";
import { t } from "../data/language";
import { ConsoleButton } from "./console-button";
import styles from "./pairing-panel.module.scss";

interface PairingPanelProps {
  qrSvg: string | null;
  expiresAt: string | null;
  receivedAt: number;
  onNewPairing: () => void;
}

export function PairingPanel({ qrSvg, expiresAt, receivedAt, onNewPairing }: PairingPanelProps) {
  const title = t("console.pairing_title");
  return (
    <section className={styles.panel}>
      <h2 className={styles.title}>{title}</h2>
      {qrSvg && expiresAt && (
        <>
          <img className={styles.qr} src={svgDataUrl(qrSvg)} alt={title} />
          <p className={styles.countdown}>
            {t("console.pairing_expires", { seconds: String(secondsUntil(expiresAt, receivedAt)) })}
          </p>
        </>
      )}
      <ConsoleButton variant={qrSvg ? "secondary" : "primary"} onClick={onNewPairing}>
        {t("console.pairing_new")}
      </ConsoleButton>
    </section>
  );
}
