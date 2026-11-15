import { describe, expect, it } from "vitest";
import { comparisonAvailable, cpuPercentValue, secondsUntil, windowProgress, svgDataUrl } from "./console-format";
import type { Session, Status } from "./contract";

const NOW = Date.parse("2026-11-01T18:00:00Z");

describe("console format", () => {
  it("pairing countdown rounds up and stops at zero", () => {
    expect([
      secondsUntil("2026-11-01T18:02:00Z", NOW),
      secondsUntil("2026-11-01T18:00:00.200Z", NOW),
      secondsUntil("2026-11-01T17:59:00Z", NOW),
    ]).toEqual([120, 1, 0]);
  });

  it("pairing window progress is the share of the two minutes left", () => {
    expect([
      windowProgress("2026-11-01T18:02:00Z", NOW),
      windowProgress("2026-11-01T18:01:00Z", NOW),
      windowProgress("2026-11-01T17:59:00Z", NOW),
    ]).toEqual([100, 50, 0]);
  });

  it("agent cpu is shown as a whole percent", () => {
    expect([cpuPercentValue(12.5), cpuPercentValue(0), cpuPercentValue(99.4)]).toEqual(["13", "0", "99"]);
  });

  it("qr svg becomes an image data url", () => {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>';

    expect(decodeURIComponent(svgDataUrl(svg))).toBe(`data:image/svg+xml;charset=utf-8,${svg}`);
  });

  it("comparison is offered only with dev tools on and a live session", () => {
    const live = { state: "live" } as Session;
    const status = (devTools: boolean, session: Session | null) => ({ devTools, session }) as Status;

    expect([
      comparisonAvailable(status(true, live)),
      comparisonAvailable(status(false, live)),
      comparisonAvailable(status(true, { state: "awaiting_confirmation" } as Session)),
      comparisonAvailable(status(true, null)),
      comparisonAvailable(null),
    ]).toEqual([true, false, false, false, false]);
  });
});
