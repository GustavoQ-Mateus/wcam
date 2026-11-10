import type { ImageDifference } from "./contract";
import { errorMessageKey, type MessageKey } from "./i18n";

export interface DifferenceLine {
  key: MessageKey;
  values: Readonly<Record<string, string>>;
}

export interface GridCell {
  text: string;
  overLimit: boolean;
}

export const VISIBLE_DELTA_E = 2;

const FAILURE_KEYS: Readonly<Record<string, MessageKey>> = {
  camera_denied: "console.dev_compare_camera_denied",
  camera_missing: "console.dev_compare_camera_missing",
  camera_busy: "console.dev_compare_camera_busy",
  camera_failed: "console.dev_compare_camera_failed",
  phone_timeout: "console.dev_compare_phone_timeout",
  phone_invalid: "console.dev_compare_phone_invalid",
  pc_missing: "console.dev_compare_pc_missing",
  timeout: "console.dev_compare_pc_missing",
  session_ended: "console.dev_compare_session_ended",
  no_live_session: "console.dev_compare_not_live",
};
const DELTA_E_DECIMALS = 1;
const TONE_DECIMALS = 1;
const CHROMA_DECIMALS = 2;
const HUE_DECIMALS = 1;
const TIME_DIGITS = 2;
const MILLISECOND_DIGITS = 3;

export function differenceLines(difference: ImageDifference): DifferenceLine[] {
  const { deltaE2000 } = difference;
  return [
    {
      key: "console.dev_compare_delta_e",
      values: {
        mean: deltaE2000.mean.toFixed(DELTA_E_DECIMALS),
        median: deltaE2000.median.toFixed(DELTA_E_DECIMALS),
        p90: deltaE2000.p90.toFixed(DELTA_E_DECIMALS),
      },
    },
    { key: "console.dev_compare_gap", values: { ms: Math.round(difference.captureGapMs).toString() } },
    { key: "console.dev_compare_tone", values: { value: signed(difference.deltaL, TONE_DECIMALS) } },
    { key: "console.dev_compare_chroma", values: { ratio: difference.chromaRatio.toFixed(CHROMA_DECIMALS) } },
    { key: "console.dev_compare_hue", values: { degrees: signed(difference.hueShiftDegrees, HUE_DECIMALS) } },
  ];
}

export function gridCells(grid: ImageDifference["grid"]): GridCell[] {
  return grid.deltaE2000.map((value) => {
    const text = value.toFixed(DELTA_E_DECIMALS);
    return { text, overLimit: Number(text) > VISIBLE_DELTA_E };
  });
}

export function comparisonFailureKey(reason: string): MessageKey {
  return FAILURE_KEYS[reason] ?? errorMessageKey(reason);
}

export function captureTime(isoTime: string): string {
  const time = new Date(isoTime);
  const clock = [time.getHours(), time.getMinutes(), time.getSeconds()]
    .map((part) => String(part).padStart(TIME_DIGITS, "0"))
    .join(":");
  return `${clock}.${String(time.getMilliseconds()).padStart(MILLISECOND_DIGITS, "0")}`;
}

export function reportDataUrl(report: unknown): string {
  return `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(report, null, 2))}`;
}

function signed(value: number, decimals: number): string {
  const text = Math.abs(value).toFixed(decimals);
  if (Number(text) === 0) {
    return text;
  }
  return value > 0 ? `+${text}` : `-${text}`;
}
