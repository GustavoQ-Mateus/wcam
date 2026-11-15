import { t } from "../data/language";
import { PrimaryButton } from "./primary-button";
import styles from "./video-playing-cover.module.scss";

interface VideoPlayingCoverProps {
  onBackToCamera: () => void;
}

export function VideoPlayingCover({ onBackToCamera }: VideoPlayingCoverProps) {
  return (
    <section className={styles.cover}>
      <div className={styles.text}>
        <h2 className={styles.title}>{t("cam.video_playing")}</h2>
        <p className={styles.body}>{t("cam.video_playing_body")}</p>
      </div>
      <div>
        <PrimaryButton onClick={onBackToCamera}>{t("cam.back_to_camera")}</PrimaryButton>
      </div>
    </section>
  );
}
