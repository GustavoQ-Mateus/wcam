import type { CamState, LiveCamState, UnavailableReason } from "../data/cam-state";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";

export type MessageState = Exclude<CamState, LiveCamState>;
export type StateMark = "waiting" | "failed";

export interface MessageAction {
  label: string;
  onClick: () => void;
}

export interface MessageContent {
  title: string;
  body?: string;
  mark?: StateMark;
  action?: MessageAction;
  reserveAction: boolean;
}

const UNAVAILABLE_KEYS: Readonly<Record<UnavailableReason, MessageKey>> = {
  unsupported: "cam.unavailable_unsupported",
  no_camera: "cam.unavailable_no_camera",
  in_use: "cam.unavailable_in_use",
};

export function messageFor(state: MessageState, onStart: () => void): MessageContent {
  const retry: MessageAction = { label: t("cam.retry"), onClick: onStart };
  switch (state.kind) {
    case "missing_pairing":
      return { title: t("cam.missing_pairing"), reserveAction: false };
    case "intro":
      return {
        title: t("cam.intro_title"),
        body: t("cam.intro_body"),
        action: { label: t("cam.intro_action"), onClick: onStart },
        reserveAction: true,
      };
    case "requesting":
      return { title: t("cam.requesting"), body: t("cam.intro_body"), mark: "waiting", reserveAction: true };
    case "denied":
      return {
        title: t("cam.denied_title"),
        body: t("cam.denied_body"),
        mark: "failed",
        action: retry,
        reserveAction: true,
      };
    case "unavailable":
      return unavailableMessage(state.reason, retry);
  }
}

function unavailableMessage(reason: UnavailableReason, retry: MessageAction): MessageContent {
  const title = t(UNAVAILABLE_KEYS[reason]);
  if (reason !== "in_use") {
    return { title, mark: "failed", reserveAction: false };
  }
  return { title, mark: "failed", action: retry, reserveAction: true };
}
