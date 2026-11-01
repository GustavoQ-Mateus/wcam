import { t } from "../data/language";
import styles from "./screen-notice.module.scss";

interface ScreenNoticeProps {
  onDismiss: () => void;
}

export function ScreenNotice({ onDismiss }: ScreenNoticeProps) {
  return (
    <button type="button" className={styles.notice} onClick={onDismiss}>
      {t("cam.keep_screen_on")}
    </button>
  );
}
