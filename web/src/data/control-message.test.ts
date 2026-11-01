import { describe, expect, it } from "vitest";
import { parseControlMessage } from "./control-message";

describe("control message", () => {
  it("session state messages from the contract are parsed", () => {
    const messages = [
      '{"type":"session_state","state":"awaiting_confirmation"}',
      '{"type":"session_state","state":"live"}',
      '{"type":"session_state","state":"ended","reason":"rejected"}',
    ].map(parseControlMessage);

    expect(messages).toEqual([
      { type: "session_state", state: "awaiting_confirmation" },
      { type: "session_state", state: "live" },
      { type: "session_state", state: "ended", reason: "rejected" },
    ]);
  });

  it("unknown or malformed messages are ignored", () => {
    const messages = ["not json", '{"type":"other","state":"live"}', '{"type":"session_state","state":"paused"}', 42];

    expect(messages.map(parseControlMessage)).toEqual([null, null, null, null]);
  });
});
