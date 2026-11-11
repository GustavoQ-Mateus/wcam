import { describe, expect, it } from "vitest";
import { constraintFailure } from "./constraint-failure";

describe("constraintFailure", () => {
  it("names the requested format and the error", () => {
    expect(constraintFailure("720p60", new DOMException("", "OverconstrainedError"))).toBe(
      "WCam could not apply 720p60 to the camera: OverconstrainedError",
    );
  });

  it("uses a generic name when the failure is not an error object", () => {
    expect(constraintFailure("continuous modes", "nope")).toBe(
      "WCam could not apply continuous modes to the camera: UnknownError",
    );
  });
});
