import { useId, type ChangeEvent } from "react";
import { t } from "../data/language";
import styles from "./comparison-panel.module.scss";
import buttonStyles from "./console-button.module.scss";

interface ScreenInputProps {
  sending: boolean;
  onFile: (file: File) => void;
}

const PNG_TYPE = "image/png";

export function ScreenInput({ sending, onFile }: ScreenInputProps) {
  const hintId = useId();
  const choose = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file?.type === PNG_TYPE) {
      onFile(file);
    }
  };
  return (
    <div className={styles.screen}>
      <label className={`${buttonStyles.button ?? ""} ${styles.screenButton ?? ""}`} data-variant="secondary">
        <input
          type="file"
          className="visually-hidden"
          accept={PNG_TYPE}
          aria-describedby={hintId}
          disabled={sending}
          onChange={choose}
        />
        {sending && <span className={styles.pendingMark} aria-hidden="true" />}
        {t("console.dev_compare_screen")}
      </label>
      <p id={hintId} className={styles.hint}>
        {t("console.dev_compare_screen_hint")}
      </p>
    </div>
  );
}
