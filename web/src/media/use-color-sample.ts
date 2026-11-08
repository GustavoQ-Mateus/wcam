import { useEffect, useRef, type RefObject } from "react";
import { colorSampleMessage, type SampleColorSpace } from "../data/color-sample";
import { createColorCanvas } from "./color-canvas";

const SAMPLE_WIDTH = 160;
const SAMPLE_HEIGHT = 90;
const SAMPLE_INTERVAL_MS = 1000;
const SAMPLES_PER_CAMERA = 5;
const SMOOTHING_QUALITY: ImageSmoothingQuality = "high";

interface SampleContext {
  context: CanvasRenderingContext2D;
  colorSpace: SampleColorSpace;
}

interface SampledCamera {
  track: MediaStreamTrack | null;
  sent: number;
}

export function useColorSample(
  videoRef: RefObject<HTMLVideoElement | null>,
  track: MediaStreamTrack | null,
  active: boolean,
  send: (data: string) => void,
): void {
  const sampledRef = useRef<SampledCamera>({ track: null, sent: 0 });

  useEffect(() => {
    if (sampledRef.current.track !== track) {
      sampledRef.current = { track, sent: 0 };
    }
  }, [track]);

  useEffect(() => {
    if (!active || !track || sampledRef.current.sent >= SAMPLES_PER_CAMERA) {
      return;
    }
    const sample = createSampleContext();
    if (!sample) {
      return;
    }
    const sampled = sampledRef.current;
    const takeSample = () => {
      const video = videoRef.current;
      if (sampled.sent >= SAMPLES_PER_CAMERA || !video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        return;
      }
      send(JSON.stringify(readSample(video, sample)));
      sampled.sent += 1;
      if (sampled.sent >= SAMPLES_PER_CAMERA) {
        window.clearInterval(timer);
      }
    };
    const timer = window.setInterval(takeSample, SAMPLE_INTERVAL_MS);
    takeSample();
    return () => {
      window.clearInterval(timer);
    };
  }, [active, track, videoRef, send]);
}

function createSampleContext(): SampleContext | null {
  const sample = createColorCanvas(SAMPLE_WIDTH, SAMPLE_HEIGHT);
  if (!sample) {
    return null;
  }
  sample.context.imageSmoothingEnabled = true;
  sample.context.imageSmoothingQuality = SMOOTHING_QUALITY;
  return { context: sample.context, colorSpace: sample.colorSpace };
}

function readSample(video: HTMLVideoElement, { context, colorSpace }: SampleContext) {
  const capturedAt = performance.timeOrigin + performance.now();
  context.drawImage(video, 0, 0, SAMPLE_WIDTH, SAMPLE_HEIGHT);
  const image = context.getImageData(0, 0, SAMPLE_WIDTH, SAMPLE_HEIGHT, { colorSpace });
  return colorSampleMessage(image.data, SAMPLE_WIDTH, SAMPLE_HEIGHT, colorSpace, capturedAt);
}
