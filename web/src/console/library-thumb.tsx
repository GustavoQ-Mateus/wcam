import { filmstripUrl } from "../data/api-client";
import type { LibraryVideo } from "../data/contract";
import { useImageSize } from "../media/use-image-size";
import styles from "./video-library.module.scss";

const THUMB_HEIGHT_PIXELS = 40;

interface LibraryThumbProps {
  video: LibraryVideo;
}

export function LibraryThumb({ video }: LibraryThumbProps) {
  const url = filmstripUrl(video.id);
  const size = useImageSize(url);
  const frames = Math.max(1, video.filmstripFrames);
  const frameWidth = size && size.height > 0 ? (THUMB_HEIGHT_PIXELS * size.width) / frames / size.height : 0;
  return (
    <span className={styles.thumbFrame} aria-hidden="true">
      {frameWidth > 0 && (
        <span
          className={styles.thumb}
          style={{
            width: frameWidth,
            height: THUMB_HEIGHT_PIXELS,
            backgroundImage: `url("${url}")`,
            backgroundSize: `${String(frameWidth * frames)}px 100%`,
          }}
        />
      )}
    </span>
  );
}
