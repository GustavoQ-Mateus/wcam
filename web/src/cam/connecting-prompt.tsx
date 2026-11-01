import { t } from "../data/language";
import styles from "./prompt.module.scss";
import { StateMark } from "./state-mark";

export function ConnectingPrompt() {
  return (
    <h1 className={styles.title}>
      <StateMark kind="waiting" />
      {t("cam.connecting")}
    </h1>
  );
}
