import { cameraCapabilitiesMessage, type CameraCapabilitiesMessage } from "../data/camera-capabilities";

const VIDEO_KIND = "video";

export function readCameraCapabilities(track: MediaStreamTrack): CameraCapabilitiesMessage {
  return cameraCapabilitiesMessage(track.getCapabilities(), track.getSettings().facingMode, senderVideoCodecs());
}

function senderVideoCodecs(): string[] {
  return RTCRtpSender.getCapabilities(VIDEO_KIND)?.codecs.map((codec) => codec.mimeType) ?? [];
}
