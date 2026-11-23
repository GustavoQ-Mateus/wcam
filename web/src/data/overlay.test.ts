import { describe, expect, it } from "vitest";
import type { Controls, Session, Status, VideoSource, VirtualCamera } from "./contract";
import { overlayRoute, panelSummary, parseOverlayMessage, quickActions } from "./overlay";

const CONTROLS: Controls = { frozen: false, cameraOff: false, mirror: false, facing: "environment" };
const VIRTUAL_CAMERA: VirtualCamera = {
  state: "active",
  backend: "media_foundation",
  reason: null,
  output: { width: 1920, height: 1080, fps: 30 },
  source: "phone",
  streamingApps: 1,
};
const VIDEO_SOURCE: VideoSource = {
  videos: [],
  timeline: { clips: [], durationSeconds: 0 },
  active: false,
  positionSeconds: null,
  decoder: null,
};
const ACTIVE_VIDEO: VideoSource = {
  videos: [
    {
      id: "v1",
      name: "loop.mp4",
      durationSeconds: 6,
      width: 1280,
      height: 720,
      fps: 30,
      codec: "h264",
      filmstripFrames: 60,
    },
  ],
  timeline: { clips: [{ id: "c1", videoId: "v1", inSeconds: 0, outSeconds: 6 }], durationSeconds: 6 },
  active: true,
  positionSeconds: 2,
  decoder: "hardware",
};
const SESSION: Session = {
  id: "s1",
  state: "live",
  deviceName: "iPhone · Safari",
  remoteIp: "192.168.0.42",
  startedAt: "2026-11-12T18:00:00Z",
  confirmationCode: "92Q-M2H",
  confirmations: { pc: true, phone: true },
  rtpPacketsBeforeLive: 0,
  video: null,
  cameraCapabilities: null,
};

function statusWith(changes: {
  session?: Partial<Session> | null;
  controls?: Partial<Controls>;
  virtualCamera?: Partial<VirtualCamera>;
  videoSource?: VideoSource;
}): Status {
  return {
    pairing: null,
    session: changes.session === null ? null : { ...SESSION, ...changes.session },
    lastEnded: null,
    virtualCamera: { ...VIRTUAL_CAMERA, ...changes.virtualCamera },
    videoFormat: { selected: "1080p30", available: ["1080p30"], camera: "1080p30", pending: false },
    process: { cpuPercent: 10 },
    quality: null,
    devTools: false,
    controls: { ...CONTROLS, ...changes.controls },
    videoSource: changes.videoSource ?? VIDEO_SOURCE,
  };
}

function labels(status: Status): string[] {
  return quickActions(status).map((action) => action.labelKey);
}

function enabled(status: Status): boolean[] {
  return quickActions(status).map((action) => action.enabled);
}

describe("overlayRoute", () => {
  it("finds each overlay window by its path", () => {
    expect([overlayRoute("/overlay/icon"), overlayRoute("/overlay/panel"), overlayRoute("/overlay/preview")]).toEqual([
      "icon",
      "panel",
      "preview",
    ]);
  });

  it("accepts a trailing slash", () => {
    expect(overlayRoute("/overlay/panel/")).toBe("panel");
  });

  it("is not an overlay window anywhere else", () => {
    expect(overlayRoute("/overlay")).toBeNull();
  });
});

describe("parseOverlayMessage", () => {
  it("reads the window state from the app", () => {
    expect(
      parseOverlayMessage({
        type: "overlay.state",
        edge: "left",
        keyboard: true,
        hotkey: "Win+Alt+W",
        floatingPreview: false,
      }),
    ).toEqual({ type: "overlay.state", edge: "left", keyboard: true, hotkey: "Win+Alt+W", floatingPreview: false });
  });

  it("reads the panel closing notice", () => {
    expect(parseOverlayMessage({ type: "panel.closing" })).toEqual({ type: "panel.closing" });
  });

  it("rejects an edge outside the four sides", () => {
    expect(
      parseOverlayMessage({
        type: "overlay.state",
        edge: "topLeft",
        keyboard: false,
        hotkey: "",
        floatingPreview: false,
      }),
    ).toBeNull();
  });

  it("rejects a state without the keyboard flag", () => {
    expect(parseOverlayMessage({ type: "overlay.state", edge: "left", floatingPreview: false })).toBeNull();
  });

  it("ignores the preview channel messages", () => {
    expect(parseOverlayMessage({ type: "preview.idle" })).toBeNull();
  });
});

describe("panelSummary", () => {
  it("names the state and the camera in use while live", () => {
    expect(panelSummary(statusWith({}))).toEqual(["state.live", "camera.back"]);
  });

  it("names only the state without a phone", () => {
    expect(panelSummary(statusWith({ session: null }))).toEqual(["state.waiting"]);
  });

  it("names only the state while a video plays", () => {
    expect(panelSummary(statusWith({ videoSource: ACTIVE_VIDEO }))).toEqual(["state.video"]);
  });
});

describe("quickActions", () => {
  it("offers freeze, camera off, the other camera and the video while live", () => {
    expect(labels(statusWith({}))).toEqual([
      "controls.freeze",
      "controls.camera_off",
      "controls.use_front",
      "controls.use_video",
    ]);
  });

  it("turns the frozen and camera off actions into their way back", () => {
    expect(labels(statusWith({ controls: { frozen: true, cameraOff: true } })).slice(0, 2)).toEqual([
      "controls.unfreeze",
      "controls.camera_on",
    ]);
  });

  it("disables the camera actions without a phone", () => {
    expect(enabled(statusWith({ session: null }))).toEqual([false, false, false, false]);
  });

  it("disables freezing and switching while the camera is off", () => {
    expect(enabled(statusWith({ controls: { cameraOff: true } }))).toEqual([false, true, false, false]);
  });

  it("offers the way back to the camera while a video plays", () => {
    expect(labels(statusWith({ videoSource: ACTIVE_VIDEO }))[3]).toBe("controls.back_to_phone");
  });

  it("asks to stop the video when going back to the camera", () => {
    expect(quickActions(statusWith({ videoSource: ACTIVE_VIDEO }))[3]).toMatchObject({ active: false, enabled: true });
  });

  it("asks for the other camera when switching", () => {
    expect(quickActions(statusWith({}))[2]).toMatchObject({ patch: { facing: "user" } });
  });
});
