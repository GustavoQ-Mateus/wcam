import { constraintFailure } from "../data/constraint-failure";
import { formatConstraints, matchesScreen, type FormatConstraints, type VideoFormat } from "../data/video-format";
import { continuousModes } from "./camera-modes";

export async function applyVideoFormat(
  track: MediaStreamTrack,
  format: VideoFormat,
  screenPortrait: boolean,
): Promise<void> {
  const size = await applySize(track, format, screenPortrait);
  if (!size) {
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

async function applySize(
  track: MediaStreamTrack,
  format: VideoFormat,
  screenPortrait: boolean,
): Promise<FormatConstraints | null> {
  const landscape = formatConstraints(format, false);
  if (!(await tryConstraints(track, format, landscape))) {
    return null;
  }
  const { width, height } = track.getSettings();
  if (!width || !height || matchesScreen({ width, height }, screenPortrait)) {
    return landscape;
  }
  const swapped = formatConstraints(format, true);
  return (await tryConstraints(track, format, swapped)) ? swapped : null;
}

async function tryConstraints(track: MediaStreamTrack, format: VideoFormat, size: FormatConstraints): Promise<boolean> {
  try {
    await track.applyConstraints(size);
    return true;
  } catch (error) {
    console.warn(constraintFailure(format, error));
    return false;
  }
}
