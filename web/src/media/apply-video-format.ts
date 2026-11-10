import { formatConstraints, type VideoFormat } from "../data/video-format";
import { continuousModes } from "./camera-modes";

export async function applyVideoFormat(track: MediaStreamTrack, format: VideoFormat, portrait: boolean): Promise<void> {
  await track
    .applyConstraints({ ...formatConstraints(format, portrait), advanced: continuousModes(track) })
    .catch(() => undefined);
}
