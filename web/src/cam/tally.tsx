import { t } from "../data/language";
import styles from "./tally.module.scss";

export function Tally() {
  return (
    <p className={styles.tally}>
      <span className={styles.lamp} aria-hidden="true" />
      {t("cam.live")}
    </p>
  );
}
