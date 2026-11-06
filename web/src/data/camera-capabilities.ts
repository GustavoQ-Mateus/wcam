import type { Facing } from "./cam-state";

export interface CameraCapabilitiesMessage {
  type: "camera_capabilities";
  width: number | null;
  height: number | null;
  frameRate: number | null;
  facingMode: Facing | null;
  codecs: string[];
}

interface Range {
  max?: number;
}

export interface TrackCapabilities {
  width?: Range;
  height?: Range;
  frameRate?: Range;
}

const EXCLUDED_CODECS: ReadonlySet<string> = new Set(["video/rtx", "video/red", "video/ulpfec"]);
const FACINGS: readonly Facing[] = ["user", "environment"];

export function cameraCapabilitiesMessage(
  capabilities: TrackCapabilities,
  facingMode: string | undefined,
  codecMimeTypes: readonly string[],
): CameraCapabilitiesMessage {
  return {
    type: "camera_capabilities",
    width: capabilities.width?.max ?? null,
    height: capabilities.height?.max ?? null,
    frameRate: capabilities.frameRate?.max ?? null,
    facingMode: FACINGS.find((facing) => facing === facingMode) ?? null,
    codecs: mediaCodecs(codecMimeTypes),
  };
}

function mediaCodecs(mimeTypes: readonly string[]): string[] {
  const codecs = mimeTypes.filter((mimeType) => !EXCLUDED_CODECS.has(mimeType.toLowerCase()));
  return [...new Set(codecs)];
}
