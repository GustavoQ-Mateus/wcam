export type SampleColorSpace = "display-p3" | "srgb";

export interface ColorSampleMessage {
  type: "color_sample";
  colorSpace: SampleColorSpace;
  width: number;
  height: number;
  rgb: string;
  capturedAt: number;
}

const RGBA_CHANNELS = 4;
const RGB_CHANNELS = 3;
const BINARY_CHUNK = 0x8000;

export function colorSampleMessage(
  rgba: Uint8ClampedArray,
  width: number,
  height: number,
  colorSpace: SampleColorSpace,
  capturedAt: number,
): ColorSampleMessage {
  return { type: "color_sample", colorSpace, width, height, rgb: toBase64(dropAlpha(rgba)), capturedAt };
}

export function dropAlpha(rgba: Uint8ClampedArray): Uint8Array {
  const pixels = rgba.length / RGBA_CHANNELS;
  const rgb = new Uint8Array(pixels * RGB_CHANNELS);
  for (let pixel = 0; pixel < pixels; pixel++) {
    rgb.set(rgba.subarray(pixel * RGBA_CHANNELS, pixel * RGBA_CHANNELS + RGB_CHANNELS), pixel * RGB_CHANNELS);
  }
  return rgb;
}

export function toBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let start = 0; start < bytes.length; start += BINARY_CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(start, start + BINARY_CHUNK));
  }
  return btoa(binary);
}
