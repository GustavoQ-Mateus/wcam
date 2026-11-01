import { t } from "../data/language";
import styles from "./prompt.module.scss";
import { RotatePhoneIcon } from "./rotate-phone-icon";

export function RotatePrompt() {
  return (
    <>
      <RotatePhoneIcon />
      <h1 className={styles.title}>{t("cam.rotate_title")}</h1>
      <p className={styles.body}>{t("cam.rotate_body")}</p>
    </>
  );
}
