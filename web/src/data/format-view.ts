import {
  chooseFrameRate,
  chooseResolution,
  formatSpec,
  frameRatesFor,
  resolutionsIn,
  type FrameRate,
  type Resolution,
  type VideoFormat,
} from "./video-format";

export interface FormatOption<T> {
  value: T;
  checked: boolean;
  pending: boolean;
  format: VideoFormat;
}

export interface FormatView {
  resolution: Resolution;
  frameRate: FrameRate;
  resolutions: FormatOption<Resolution>[];
  frameRates: FormatOption<FrameRate>[];
}

const MINIMUM_CHOICES = 2;

export function formatView(
  confirmed: VideoFormat,
  available: readonly VideoFormat[],
  pending: VideoFormat | null,
): FormatView {
  const { resolution, frameRate } = formatSpec(confirmed);
  const pendingSpec = pending ? formatSpec(pending) : null;
  const resolutions = resolutionsIn(available).flatMap((value) => {
    const format = chooseResolution(confirmed, value, available);
    if (!format) {
      return [];
    }
    const isPending = pendingSpec !== null && pendingSpec.resolution === value && value !== resolution;
    return [{ value, checked: value === resolution, pending: isPending, format }];
  });
  const frameRates = frameRatesFor(resolution, available).flatMap((value) => {
    const format = chooseFrameRate(confirmed, value, available);
    if (!format) {
      return [];
    }
    const isPending = pendingSpec !== null && pendingSpec.frameRate === value && value !== frameRate;
    return [{ value, checked: value === frameRate, pending: isPending, format }];
  });
  return {
    resolution,
    frameRate,
    resolutions: resolutions.length >= MINIMUM_CHOICES ? resolutions : [],
    frameRates: frameRates.length >= MINIMUM_CHOICES ? frameRates : [],
  };
}
