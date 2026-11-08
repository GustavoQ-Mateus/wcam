import type { SampleColorSpace } from "../data/color-sample";

export interface ColorCanvas {
  canvas: HTMLCanvasElement;
  context: CanvasRenderingContext2D;
  colorSpace: SampleColorSpace;
}

const PREFERRED_COLOR_SPACE: SampleColorSpace = "display-p3";
const FALLBACK_COLOR_SPACE: SampleColorSpace = "srgb";
const PNG_TYPE = "image/png";

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

export function encodePng(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error("Canvas could not be encoded as PNG"));
      }
    }, PNG_TYPE);
  });
}
