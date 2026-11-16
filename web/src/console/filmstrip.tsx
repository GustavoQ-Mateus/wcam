import { filmstripUrl } from "../data/api-client";
import type { LibraryVideo } from "../data/contract";
import { filmstripFrame, TRACK_HEIGHT_PIXELS } from "../data/timeline";
import { useImageSize } from "../media/use-image-size";
import styles from "./filmstrip.module.scss";

const MAX_THUMBS = 240;

interface FilmstripProps {
  video: LibraryVideo;
  inSeconds: number;
  outSeconds: number;
  pixelsPerSecond: number;
}

export function Filmstrip({ video, inSeconds, outSeconds, pixelsPerSecond }: FilmstripProps) {
  const url = filmstripUrl(video.id);
  const size = useImageSize(url);
  if (!size || size.height === 0 || video.filmstripFrames === 0) {
    return <div className={styles.strip} />;
  }
  const frameWidth = size.width / video.filmstripFrames;
  const thumbWidth = (TRACK_HEIGHT_PIXELS * frameWidth) / size.height;
  const clipWidth = (outSeconds - inSeconds) * pixelsPerSecond;
  const count = Math.min(MAX_THUMBS, Math.max(1, Math.ceil(clipWidth / thumbWidth)));
  return (
    <div className={styles.strip} aria-hidden="true">
      {Array.from({ length: count }, (_, index) => {
        const seconds = inSeconds + ((index + 0.5) * thumbWidth) / pixelsPerSecond;
        const frame = filmstripFrame(video, Math.min(seconds, outSeconds));
        return (
          <span
            key={index}
            className={styles.thumb}
            style={{
              width: thumbWidth,
              backgroundImage: `url("${url}")`,
              backgroundSize: `${String(thumbWidth * video.filmstripFrames)}px 100%`,
              backgroundPosition: `${String(-frame * thumbWidth)}px 0`,
            }}
          />
        );
      })}
    </div>
  );
}
