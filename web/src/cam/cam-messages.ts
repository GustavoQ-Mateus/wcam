import type { BlockedReason, CamState, EndedReason, LiveCamState, UnavailableReason } from "../data/cam-state";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import type { StateMarkKind } from "./state-mark";

export type MessageState = Exclude<CamState, LiveCamState>;

export interface MessageAction {
  label: string;
  onClick: () => void;
}

export interface MessageContent {
  title: string;
  body?: string;
  mark?: StateMarkKind;
  action?: MessageAction;
  reserveAction: boolean;
}

const UNAVAILABLE_KEYS: Readonly<Record<UnavailableReason, MessageKey>> = {
  unsupported: "cam.unavailable_unsupported",
  no_camera: "cam.unavailable_no_camera",
  in_use: "cam.unavailable_in_use",
};
const BLOCKED_KEYS: Readonly<Record<BlockedReason, MessageKey>> = {
  network: "cam.blocked_network",
  attempts: "cam.blocked_attempts",
};
const ENDED_KEYS: Readonly<Record<EndedReason, MessageKey>> = {
  rejected: "cam.ended_rejected",
  code_different: "cam.ended_code_different",
  disconnected: "cam.ended_disconnected",
  lost: "cam.ended_lost",
  timeout: "cam.ended_timeout",
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
    case "pairing_failed":
      return failedMessage("cam.pairing_failed");
    case "blocked":
      return failedMessage(BLOCKED_KEYS[state.reason]);
    case "busy":
      return failedMessage("cam.busy");
    case "ended":
      return state.reason === "disconnected"
        ? { title: t(ENDED_KEYS[state.reason]), reserveAction: false }
        : failedMessage(ENDED_KEYS[state.reason]);
  }
}

function failedMessage(key: MessageKey): MessageContent {
  return { title: t(key), mark: "failed", reserveAction: false };
}

function unavailableMessage(reason: UnavailableReason, retry: MessageAction): MessageContent {
  const title = t(UNAVAILABLE_KEYS[reason]);
  if (reason !== "in_use") {
    return { title, mark: "failed", reserveAction: false };
  }
  return { title, mark: "failed", action: retry, reserveAction: true };
}
