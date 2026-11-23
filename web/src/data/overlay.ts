import type { ControlsPatch, Status } from "./contract";
import { consoleMode, currentFacing, isLiveMode, otherFacing, stateBadge } from "./console-view";
import type { MessageKey } from "./i18n";

export type OverlayRoute = "icon" | "panel" | "preview";

export type OverlayEdge = "left" | "right" | "top" | "bottom";

export type ResizeEdge = "left" | "right" | "top" | "bottom" | "topLeft" | "topRight" | "bottomLeft" | "bottomRight";

export interface OverlayState {
  edge: OverlayEdge;
  keyboard: boolean;
  hotkey: string;
  floatingPreview: boolean;
}

export type OverlayAppMessage = ({ type: "overlay.state" } & OverlayState) | { type: "panel.closing" };

export type OverlayPageMessage =
  | { type: "window.drag" }
  | { type: "window.resize"; edge: ResizeEdge }
  | { type: "window.size"; width: number; height: number }
  | { type: "panel.open" }
  | { type: "panel.close" }
  | { type: "console.open" }
  | { type: "overlay.hide" }
  | { type: "floatingPreview.toggle" };

export type QuickAction =
  | { kind: "controls"; labelKey: MessageKey; pressed: boolean; enabled: boolean; patch: ControlsPatch }
  | { kind: "video_source"; labelKey: MessageKey; enabled: boolean; active: boolean };

export const DEFAULT_OVERLAY_STATE: OverlayState = {
  edge: "right",
  keyboard: false,
  hotkey: "",
  floatingPreview: false,
};

const ROUTES: Record<string, OverlayRoute> = {
  "/overlay/icon": "icon",
  "/overlay/panel": "panel",
  "/overlay/preview": "preview",
};
const EDGES: ReadonlySet<unknown> = new Set(["left", "right", "top", "bottom"]);
const FACING_KEYS = { user: "camera.front", environment: "camera.back" } as const;

export function overlayRoute(path: string): OverlayRoute | null {
  return ROUTES[path.replace(/\/$/, "")] ?? null;
}

export function parseOverlayMessage(data: unknown): OverlayAppMessage | null {
  if (typeof data !== "object" || data === null) {
    return null;
  }
  const message = data as Record<string, unknown>;
  if (message.type === "panel.closing") {
    return { type: "panel.closing" };
  }
  if (message.type !== "overlay.state" || !EDGES.has(message.edge)) {
    return null;
  }
  if (typeof message.keyboard !== "boolean" || typeof message.floatingPreview !== "boolean") {
    return null;
  }
  return {
    type: "overlay.state",
    edge: message.edge as OverlayEdge,
    keyboard: message.keyboard,
    hotkey: typeof message.hotkey === "string" ? message.hotkey : "",
    floatingPreview: message.floatingPreview,
  };
}

export function panelSummary(status: Status): MessageKey[] {
  const badge = stateBadge(status).key;
  const facing = currentFacing(status);
  const showsFacing = facing !== null && isLiveMode(consoleMode(status)) && !status.videoSource.active;
  return showsFacing ? [badge, FACING_KEYS[facing]] : [badge];
}

export function quickActions(status: Status): QuickAction[] {
  const { controls, videoSource, session } = status;
  const live = session?.state === "live" && !videoSource.active;
  const other = otherFacing(currentFacing(status));
  return [
    {
      kind: "controls",
      labelKey: controls.frozen ? "controls.unfreeze" : "controls.freeze",
      pressed: controls.frozen,
      enabled: (live || videoSource.active) && !controls.cameraOff,
      patch: { frozen: !controls.frozen },
    },
    {
      kind: "controls",
      labelKey: controls.cameraOff ? "controls.camera_on" : "controls.camera_off",
      pressed: controls.cameraOff,
      enabled: live,
      patch: { cameraOff: !controls.cameraOff },
    },
    {
      kind: "controls",
      labelKey: other === "user" ? "controls.use_front" : "controls.use_back",
      pressed: false,
      enabled: live && !controls.cameraOff,
      patch: { facing: other },
    },
    {
      kind: "video_source",
      labelKey: videoSource.active ? "controls.back_to_phone" : "controls.use_video",
      enabled: videoSource.active || videoSource.timeline.clips.length > 0,
      active: !videoSource.active,
    },
  ];
}
