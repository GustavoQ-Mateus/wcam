import { t } from "../data/language";
import styles from "./frozen-notice.module.scss";

export function FrozenNotice() {
  return (
    <p className={styles.notice} role="status">
      <span className={styles.mark} aria-hidden="true" />
      {t("cam.frozen")}
    </p>
  );
}
