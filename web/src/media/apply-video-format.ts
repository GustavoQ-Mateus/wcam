import { constraintFailure } from "../data/constraint-failure";
import { formatConstraints, type VideoFormat } from "../data/video-format";
import { continuousModes } from "./camera-modes";

export async function applyVideoFormat(track: MediaStreamTrack, format: VideoFormat, portrait: boolean): Promise<void> {
  const size = formatConstraints(format, portrait);
  try {
    await track.applyConstraints(size);
  } catch (error) {
    console.warn(constraintFailure(format, error));
    return;
  }
  // Chromium keeps the old size when camera modes come in the same call.
  const advanced = continuousModes(track);
  if (advanced.length > 0) {
    await track.applyConstraints({ ...size, advanced }).catch((error: unknown) => {
      console.warn(constraintFailure(format, error));
    });
  }
}
