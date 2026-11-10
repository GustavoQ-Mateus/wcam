import { t } from "./language";
import { formatSpec, frameRateKey, resolutionKey, type VideoFormat } from "./video-format";

export function formatName(format: VideoFormat): string {
  const { resolution, frameRate } = formatSpec(format);
  return t("format.name", { resolution: t(resolutionKey(resolution)), frameRate: t(frameRateKey(frameRate)) });
}
