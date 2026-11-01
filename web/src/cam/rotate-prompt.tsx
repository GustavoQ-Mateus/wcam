import { t } from "../data/language";
import { RotatePhoneIcon } from "./rotate-phone-icon";
import styles from "./rotate-prompt.module.scss";

export function RotatePrompt() {
  return (
    <section className={styles.prompt} aria-live="polite">
      <RotatePhoneIcon />
      <h1 className={styles.title}>{t("cam.rotate_title")}</h1>
      <p className={styles.body}>{t("cam.rotate_body")}</p>
    </section>
  );
}
