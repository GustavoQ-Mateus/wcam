import { t } from "../data/language";
import styles from "./preview-cover.module.scss";

interface PreviewCoverProps {
  visible: boolean;
  onShow: () => void;
}

export function PreviewCover({ visible, onShow }: PreviewCoverProps) {
  return (
    <button type="button" className={styles.cover} data-visible={visible} inert={!visible} onClick={onShow}>
      <span className={styles.text}>{t("cam.preview_hidden")}</span>
    </button>
  );
}
