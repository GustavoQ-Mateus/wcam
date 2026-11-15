import { describe, expect, it } from "vitest";
import { nextPreviewState } from "./preview-state";

describe("nextPreviewState", () => {
  it("shows the preview only once a frame arrives", () => {
    expect(nextPreviewState("connecting", "frame")).toBe("showing");
  });

  it("stops when no frame arrives in time", () => {
    expect(nextPreviewState("connecting", "no_frame")).toBe("stopped");
  });

  it("keeps showing when the first frame timer fires after a frame", () => {
    expect(nextPreviewState("showing", "no_frame")).toBe("showing");
  });

  it("stops when the connection ends while connecting", () => {
    expect(nextPreviewState("connecting", "connection_ended")).toBe("stopped");
  });

  it("stops when the connection ends while showing", () => {
    expect(nextPreviewState("showing", "connection_ended")).toBe("stopped");
  });

  it("stays stopped on a late frame", () => {
    expect(nextPreviewState("stopped", "frame")).toBe("stopped");
  });

  it("stays stopped until started again", () => {
    expect(nextPreviewState("stopped", "connection_ended")).toBe("stopped");
    expect(nextPreviewState("stopped", "no_frame")).toBe("stopped");
  });

  it("connects again when started after stopping", () => {
    expect(nextPreviewState("stopped", "start")).toBe("connecting");
  });

  it("waits for a new frame when started while showing", () => {
    expect(nextPreviewState("showing", "start")).toBe("connecting");
  });
});
