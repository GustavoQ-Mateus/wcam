import type { SampleColorSpace } from "../data/color-sample";

export interface ColorCanvas {
  canvas: HTMLCanvasElement;
  context: CanvasRenderingContext2D;
  colorSpace: SampleColorSpace;
}

const PREFERRED_COLOR_SPACE: SampleColorSpace = "display-p3";
const FALLBACK_COLOR_SPACE: SampleColorSpace = "srgb";

export function createColorCanvas(
  width: number,
  height: number,
  colorSpace: SampleColorSpace = PREFERRED_COLOR_SPACE,
): ColorCanvas | null {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { colorSpace, willReadFrequently: true });
  if (!context) {
    return null;
  }
  const granted = context.getContextAttributes().colorSpace === colorSpace ? colorSpace : FALLBACK_COLOR_SPACE;
  return { canvas, context, colorSpace: granted };
}

export function encodePng(canvas: HTMLCanvasElement): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("Canvas could not be encoded as PNG"));
        return;
      }
      blob.arrayBuffer().then((buffer) => {
        resolve(new Uint8Array(buffer));
      }, reject);
    }, "image/png");
  });
}
