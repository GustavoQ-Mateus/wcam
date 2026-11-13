import { t } from "../data/language";
import styles from "./camera-off-cover.module.scss";
import { PrimaryButton } from "./primary-button";

interface CameraOffCoverProps {
  onCameraOn: () => void;
}

export function CameraOffCover({ onCameraOn }: CameraOffCoverProps) {
  return (
    <section className={styles.cover}>
      <h2 className={styles.title}>{t("cam.camera_off")}</h2>
      <div>
        <PrimaryButton onClick={onCameraOn}>{t("controls.camera_on")}</PrimaryButton>
      </div>
    </section>
  );
}
