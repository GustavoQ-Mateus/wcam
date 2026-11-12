type Json = Record<string, unknown>;

const FRAME_WAIT_MS = 1500;
const CAPABILITY_KEYS = [
  "zoom",
  "torch",
  "focusMode",
  "focusDistance",
  "pointsOfInterest",
  "exposureCompensation",
  "exposureMode",
  "whiteBalanceMode",
  "width",
  "height",
  "frameRate",
  "facingMode",
  "aspectRatio",
  "resizeMode",
];

const statusElement = document.querySelector<HTMLParagraphElement>("#status")!;
const outputElement = document.querySelector<HTMLPreElement>("#output")!;
const localVideo = document.querySelector<HTMLVideoElement>("#local")!;
const remoteVideo = document.querySelector<HTMLVideoElement>("#remote")!;
const result: Json = { userAgent: navigator.userAgent, startedAt: new Date().toISOString() };

function show(status: string): void {
  statusElement.textContent = status;
  outputElement.textContent = JSON.stringify(result, null, 2);
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function errorText(error: unknown): string {
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
}

async function frameSize(video: HTMLVideoElement): Promise<Json> {
  await wait(FRAME_WAIT_MS);
  return { width: video.videoWidth, height: video.videoHeight };
}

async function openCamera(deviceId: string): Promise<MediaStreamTrack> {
  const stream = await navigator.mediaDevices.getUserMedia({ video: { deviceId: { exact: deviceId } } });
  return stream.getVideoTracks()[0]!;
}

async function showTrack(video: HTMLVideoElement, track: MediaStreamTrack): Promise<void> {
  video.srcObject = new MediaStream([track]);
  await video.play().catch(() => undefined);
}

function pickCapabilities(capabilities: Json): Json {
  const picked: Json = { keys: Object.keys(capabilities) };
  for (const key of CAPABILITY_KEYS) picked[key] = capabilities[key] ?? null;
  return picked;
}

function zoomTargets(zoom: Json): number[] {
  const min = Number(zoom.min);
  const max = Number(zoom.max);
  const targets = [min, 1, 2, max].filter((value) => value >= min && value <= max);
  return [...new Set(targets)];
}

async function measureZoom(track: MediaStreamTrack, zoom: Json): Promise<Json[]> {
  const steps: Json[] = [];
  for (const target of zoomTargets(zoom)) {
    const step: Json = { target };
    try {
      await track.applyConstraints({ advanced: [{ zoom: target } as MediaTrackConstraintSet] });
      step.settings = track.getSettings();
      step.frame = await frameSize(localVideo);
    } catch (error) {
      step.error = errorText(error);
    }
    steps.push(step);
  }
  return steps;
}

async function measureDevice(device: MediaDeviceInfo): Promise<Json> {
  const entry: Json = { label: device.label, deviceId: device.deviceId, groupId: device.groupId };
  try {
    const track = await openCamera(device.deviceId);
    await showTrack(localVideo, track);
    const capabilities = (track.getCapabilities?.() ?? {}) as Json;
    entry.capabilities = pickCapabilities(capabilities);
    entry.capabilitiesFull = capabilities;
    entry.settings = track.getSettings();
    entry.frame = await frameSize(localVideo);
    if (capabilities.zoom) entry.zoomSteps = await measureZoom(track, capabilities.zoom as Json);
    track.stop();
  } catch (error) {
    entry.error = errorText(error);
  }
  return entry;
}

async function connectLoopback(track: MediaStreamTrack): Promise<RTCPeerConnection[]> {
  const sender = new RTCPeerConnection();
  const receiver = new RTCPeerConnection();
  sender.onicecandidate = (event) => event.candidate && receiver.addIceCandidate(event.candidate);
  receiver.onicecandidate = (event) => event.candidate && sender.addIceCandidate(event.candidate);
  receiver.ontrack = (event) => void showTrack(remoteVideo, event.track);
  const transceiver = sender.addTransceiver("video", { direction: "sendonly" });
  await transceiver.sender.replaceTrack(track);
  await sender.setLocalDescription(await sender.createOffer());
  await receiver.setRemoteDescription(sender.localDescription!);
  await receiver.setLocalDescription(await receiver.createAnswer());
  await sender.setRemoteDescription(receiver.localDescription!);
  return [sender, receiver];
}

async function framesDecoded(receiver: RTCPeerConnection): Promise<number> {
  let decoded = 0;
  (await receiver.getStats()).forEach((report: Json) => {
    if (report.type === "inbound-rtp" && report.kind === "video") decoded = Number(report.framesDecoded ?? 0);
  });
  return decoded;
}

async function measureReplaceTrack(devices: MediaDeviceInfo[]): Promise<Json[]> {
  const outcomes: Json[] = [];
  const first = await openCamera(devices[0]!.deviceId);
  const [sender, receiver] = await connectLoopback(first);
  await wait(FRAME_WAIT_MS * 2);
  let current = first;
  let label = devices[0]!.label;
  for (const device of devices.slice(1)) {
    const outcome: Json = { from: label, to: device.label };
    try {
      const before = await framesDecoded(receiver!);
      current.stop();
      current = await openCamera(device.deviceId);
      await sender!.getSenders()[0]!.replaceTrack(current);
      await wait(FRAME_WAIT_MS * 2);
      outcome.framesDecodedDelta = (await framesDecoded(receiver!)) - before;
      outcome.remoteFrame = { width: remoteVideo.videoWidth, height: remoteVideo.videoHeight };
      outcome.settings = current.getSettings();
      label = device.label;
    } catch (error) {
      outcome.error = errorText(error);
    }
    outcomes.push(outcome);
  }
  current.stop();
  sender!.close();
  receiver!.close();
  return outcomes;
}

async function saveResult(): Promise<void> {
  const response = await fetch("/spike-result", { method: "POST", body: JSON.stringify(result) });
  result.savedOnComputer = response.ok;
}

async function run(): Promise<void> {
  show("Pedindo permissão...");
  const permission = await navigator.mediaDevices.getUserMedia({ video: true });
  permission.getTracks().forEach((track) => track.stop());
  const devices = (await navigator.mediaDevices.enumerateDevices()).filter((device) => device.kind === "videoinput");
  result.devices = devices.map((device) => device.label);
  result.supportedConstraints = navigator.mediaDevices.getSupportedConstraints();
  const cameras: Json[] = [];
  result.cameras = cameras;
  for (const [index, device] of devices.entries()) {
    show(`Medindo câmera ${index + 1} de ${devices.length}: ${device.label}`);
    cameras.push(await measureDevice(device));
  }
  show("Testando troca de câmera com a conexão aberta...");
  try {
    result.replaceTrack = await measureReplaceTrack(devices);
  } catch (error) {
    result.replaceTrack = { error: errorText(error) };
  }
  result.finishedAt = new Date().toISOString();
  await saveResult().catch((error: unknown) => (result.savedOnComputer = errorText(error)));
  show(result.savedOnComputer === true ? "Pronto. Resultado salvo no computador." : "Pronto. Copie o resultado.");
}

document.querySelector("#start")!.addEventListener("click", () => {
  run().catch((error: unknown) => {
    result.fatal = errorText(error);
    show("Falhou. Copie o resultado.");
  });
});

document.querySelector("#copy")!.addEventListener("click", () => {
  void navigator.clipboard.writeText(JSON.stringify(result, null, 2));
});
