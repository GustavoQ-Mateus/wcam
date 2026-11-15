import { describe, expect, it } from "vitest";
import { createPublisherGate } from "./publisher-gate";

const CAMERA = "camera";
const OTHER_CAMERA = "other-camera";

function openGate() {
  const replaced: (string | null)[] = [];
  const sent: string[] = [];
  const gate = createPublisherGate<string>({
    replaceTrack: (track) => replaced.push(track),
    send: (data) => sent.push(data),
  });
  return { gate, replaced, sent };
}

describe("publisher gate", () => {
  it("does not hand the camera to the connection before live", () => {
    const { gate, replaced } = openGate();
    gate.setTrack(CAMERA);
    gate.setTrack(OTHER_CAMERA);
    expect(replaced).toEqual([]);
  });

  it("hands the current camera to the connection when live arrives", () => {
    const { gate, replaced } = openGate();
    gate.setTrack(CAMERA);
    gate.goLive();
    expect(replaced).toEqual([CAMERA]);
  });

  it("hands nothing when live arrives without a camera", () => {
    const { gate, replaced } = openGate();
    gate.goLive();
    expect(replaced).toEqual([]);
  });

  it("replaces the camera after live", () => {
    const { gate, replaced } = openGate();
    gate.setTrack(CAMERA);
    gate.goLive();
    gate.setTrack(OTHER_CAMERA);
    gate.setTrack(null);
    expect(replaced).toEqual([CAMERA, OTHER_CAMERA, null]);
  });

  it("drops every message before live", () => {
    const { gate, sent } = openGate();
    gate.send('{"type":"camera_capabilities"}');
    gate.send('{"type":"set_video_format","format":"720p30"}');
    expect(sent).toEqual([]);
  });

  it("sends messages after live", () => {
    const { gate, sent } = openGate();
    gate.goLive();
    gate.send('{"type":"stats"}');
    expect(sent).toEqual(['{"type":"stats"}']);
  });

  it("sends confirm code before live", () => {
    const { gate, sent } = openGate();
    gate.confirmCode();
    expect(sent.map((data) => JSON.parse(data) as unknown)).toEqual([{ type: "confirm_code" }]);
  });

  it("sends reject code before live", () => {
    const { gate, sent } = openGate();
    gate.rejectCode();
    expect(sent.map((data) => JSON.parse(data) as unknown)).toEqual([{ type: "reject_code" }]);
  });

  it("answers the code only once", () => {
    const { gate, sent } = openGate();
    gate.confirmCode();
    gate.rejectCode();
    gate.confirmCode();
    expect(sent).toHaveLength(1);
  });

  it("does not answer the code after live", () => {
    const { gate, sent } = openGate();
    gate.goLive();
    gate.confirmCode();
    gate.rejectCode();
    expect(sent).toEqual([]);
  });

  it("only ever sends the code answer before live", () => {
    const { gate, sent, replaced } = openGate();
    gate.setTrack(CAMERA);
    gate.send('{"type":"camera_capabilities"}');
    gate.confirmCode();
    gate.send('{"type":"set_controls","mirror":true}');
    expect(replaced).toEqual([]);
    expect(sent.map((data) => (JSON.parse(data) as { type: string }).type)).toEqual(["confirm_code"]);
  });
});
