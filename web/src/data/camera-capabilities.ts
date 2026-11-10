import type { Facing } from "./cam-state";

export interface CameraCapabilitiesMessage {
  type: "camera_capabilities";
  width: number | null;
  height: number | null;
  frameRate: number | null;
  facingMode: Facing | null;
  codecs: string[];
  colorSpace: CameraColorSpace | null;
}

export interface CameraColorSpace {
  primaries: string | null;
  transfer: string | null;
  matrix: string | null;
  fullRange: boolean | null;
}

export interface DeclaredColorSpace {
  primaries?: string | null;
  transfer?: string | null;
  matrix?: string | null;
  fullRange?: boolean | null;
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
  colorSpace: DeclaredColorSpace | null,
): CameraCapabilitiesMessage {
  return {
    type: "camera_capabilities",
    width: capabilities.width?.max ?? null,
    height: capabilities.height?.max ?? null,
    frameRate: capabilities.frameRate?.max ?? null,
    facingMode: FACINGS.find((facing) => facing === facingMode) ?? null,
    codecs: mediaCodecs(codecMimeTypes),
    colorSpace: colorSpace && cameraColorSpace(colorSpace),
  };
}

function cameraColorSpace({ primaries, transfer, matrix, fullRange }: DeclaredColorSpace): CameraColorSpace {
  return {
    primaries: primaries ?? null,
    transfer: transfer ?? null,
    matrix: matrix ?? null,
    fullRange: fullRange ?? null,
  };
}

function mediaCodecs(mimeTypes: readonly string[]): string[] {
  const codecs = mimeTypes.filter((mimeType) => !EXCLUDED_CODECS.has(mimeType.toLowerCase()));
  return [...new Set(codecs)];
}
