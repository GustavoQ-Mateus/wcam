import { useEffect } from "react";
import type { RefObject } from "react";
import { snapshotMessages } from "../data/snapshot";
import { createColorCanvas, encodePng } from "./color-canvas";
import type { SnapshotRequest } from "./use-publisher";

export function useSnapshotResponder(
  videoRef: RefObject<HTMLVideoElement | null>,
  request: SnapshotRequest | null,
  live: boolean,
  sendPaced: (messages: readonly string[]) => Promise<void>,
): void {
  useEffect(() => {
    const video = videoRef.current;
    if (!request || !live || !video || video.videoWidth === 0) {
      return;
    }
    void sendSnapshot(request.id, video, sendPaced);
  }, [request, live, videoRef, sendPaced]);
}

async function sendSnapshot(
  id: string,
  video: HTMLVideoElement,
  sendPaced: (messages: readonly string[]) => Promise<void>,
): Promise<void> {
  const { videoWidth: width, videoHeight: height } = video;
  const frame = createColorCanvas(width, height);
  if (!frame) {
    return;
  }
  const capturedAt = performance.timeOrigin + performance.now();
  frame.context.drawImage(video, 0, 0, width, height);
  const png = await encodePng(frame.canvas).catch(() => null);
  if (!png) {
    return;
  }
  await sendPaced(snapshotMessages({ id, capturedAt, colorSpace: frame.colorSpace, width, height, png }));
}
