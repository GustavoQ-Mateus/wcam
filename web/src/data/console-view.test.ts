import { describe, expect, it } from "vitest";
import type { Controls, Session, Status, VirtualCamera } from "./contract";
import {
  consoleMode,
  currentFacing,
  otherFacing,
  problemKey,
  signalPath,
  stateBadge,
  type PathStep,
} from "./console-view";

const CONTROLS: Controls = { frozen: false, cameraOff: false, mirror: false, facing: "environment" };
const VIRTUAL_CAMERA: VirtualCamera = {
  state: "active",
  backend: "media_foundation",
  reason: null,
  output: { width: 1920, height: 1080, fps: 30 },
  source: "phone",
  streamingApps: 1,
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
  };
}

function states(path: PathStep[]): string[] {
  return path.map((step) => step.state);
}

describe("console view", () => {
  it("no phone means waiting for the phone", () => {
    expect(consoleMode(statusWith({ session: null }))).toBe("waiting");
  });

  it("each session state before live has its own mode", () => {
    const modes = (["connecting", "awaiting_confirmation"] as const).map((state) =>
      consoleMode(statusWith({ session: { state } })),
    );

    expect(modes).toEqual(["connecting", "confirming"]);
  });

  it("camera off wins over a frozen image", () => {
    expect(consoleMode(statusWith({ controls: { frozen: true, cameraOff: true } }))).toBe("camera_off");
  });

  it("an image frozen by the user is frozen", () => {
    expect(consoleMode(statusWith({ controls: { frozen: true } }))).toBe("frozen");
  });

  it("a live session whose camera repeats the last frame has lost the signal", () => {
    expect(consoleMode(statusWith({ virtualCamera: { source: "frozen" } }))).toBe("lost");
  });

  it("each state has its own badge text, colour and shape", () => {
    const badges = [
      statusWith({ session: null }),
      statusWith({ session: { state: "awaiting_confirmation" } }),
      statusWith({}),
      statusWith({ controls: { frozen: true } }),
      statusWith({ controls: { cameraOff: true } }),
      statusWith({ virtualCamera: { source: "frozen" } }),
    ].map(stateBadge);

    expect(badges).toEqual([
      { key: "state.waiting", tone: "neutral", shape: "ring" },
      { key: "state.confirming", tone: "warning", shape: "triangle" },
      { key: "state.live", tone: "live", shape: "dot" },
      { key: "state.frozen", tone: "still", shape: "square" },
      { key: "state.camera_off", tone: "warning", shape: "bars" },
      { key: "state.lost", tone: "negative", shape: "triangle" },
    ]);
  });

  it("an unavailable virtual camera is a problem with its own fix", () => {
    const status = statusWith({ virtualCamera: { state: "unavailable", reason: "driver_missing" } });

    expect(stateBadge(status).key).toBe("state.problem");
    expect(problemKey(status)).toBe("console.virtual_camera_driver_missing");
  });

  it("an active virtual camera has no problem to fix", () => {
    expect(problemKey(statusWith({}))).toBeNull();
  });

  it("the signal path is all working while live", () => {
    expect(states(signalPath(statusWith({})))).toEqual(["ok", "ok", "ok", "ok"]);
  });

  it("the signal path waits on the phone and the network before the phone arrives", () => {
    expect(states(signalPath(statusWith({ session: null })))).toEqual(["waiting", "waiting", "ok", "ok"]);
  });

  it("a lost signal marks the phone and the network as the problem", () => {
    const path = signalPath(statusWith({ virtualCamera: { source: "frozen" } }));

    expect(states(path)).toEqual(["problem", "problem", "ok", "ok"]);
  });

  it("a camera turned off leaves the phone waiting with the network working", () => {
    expect(states(signalPath(statusWith({ controls: { cameraOff: true } })))).toEqual(["waiting", "ok", "ok", "ok"]);
  });

  it("the apps step counts the apps using the camera", () => {
    const apps = [0, 1, 2, null].map(
      (streamingApps) => signalPath(statusWith({ virtualCamera: { streamingApps } }))[3],
    );

    expect(apps).toEqual([
      { nameKey: "console.path_apps", state: "waiting", noteKey: "console.apps_none" },
      { nameKey: "console.path_apps", state: "ok", noteKey: "console.apps_one" },
      { nameKey: "console.path_apps", state: "ok", noteKey: "console.apps_count", count: 2 },
      { nameKey: "console.path_apps", state: "ok", noteKey: "console.path_ok" },
    ]);
  });

  it("the camera in use comes from the phone and falls back to the one asked for", () => {
    const fromPhone = statusWith({
      session: {
        cameraCapabilities: {
          width: null,
          height: null,
          frameRate: null,
          facingMode: "user",
          codecs: [],
          colorSpace: null,
          modes: { exposureMode: null, whiteBalanceMode: null, focusMode: null },
        },
      },
    });

    expect([currentFacing(fromPhone), currentFacing(statusWith({}))]).toEqual(["user", "environment"]);
  });

  it("the other camera of the front one is the back one and the other way round", () => {
    expect([otherFacing("user"), otherFacing("environment"), otherFacing(null)]).toEqual([
      "environment",
      "user",
      "user",
    ]);
  });
});
