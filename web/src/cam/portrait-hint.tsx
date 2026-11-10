import { t } from "../data/language";
import styles from "./portrait-hint.module.scss";

export function PortraitHint() {
  return <p className={styles.hint}>{t("cam.portrait_hint")}</p>;
}
