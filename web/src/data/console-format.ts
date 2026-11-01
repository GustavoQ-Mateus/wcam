import type { Video } from "./contract";

const MILLISECONDS_PER_SECOND = 1000;
const KILOBITS_PER_MEGABIT = 1000;
const FPS_DECIMALS = 1;
const BITRATE_DECIMALS = 1;
const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const SVG_NAMESPACE_PATTERN = /<svg[^>]*\sxmlns=/;
const SVG_TAG = "<svg";

export function secondsUntil(expiresAt: string, now: number): number {
  return Math.max(0, Math.ceil((Date.parse(expiresAt) - now) / MILLISECONDS_PER_SECOND));
}

export function videoFormatValues(video: Video): Readonly<Record<string, string>> {
  return {
    width: String(video.width),
    height: String(video.height),
    fps: video.fps.toFixed(FPS_DECIMALS),
    bitrate: (video.bitrateKbps / KILOBITS_PER_MEGABIT).toFixed(BITRATE_DECIMALS),
  };
}

export function svgDataUrl(svg: string): string {
  const standalone = SVG_NAMESPACE_PATTERN.test(svg) ? svg : svg.replace(SVG_TAG, `<svg xmlns="${SVG_NAMESPACE}"`);
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(standalone)}`;
}
