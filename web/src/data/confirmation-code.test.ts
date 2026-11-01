import { describe, expect, it } from "vitest";
import { confirmationCode, sdpFingerprint } from "./confirmation-code";

const AB = Array<string>(32).fill("AB").join(":");
const CD = Array<string>(32).fill("CD").join(":");

describe("confirmation code", () => {
  it("confirmation code matches the three contract vectors", async () => {
    const codes = await Promise.all([
      confirmationCode("00112233445566778899aabbccddeeff", AB, CD),
      confirmationCode("00112233445566778899aabbccddeeff", CD, AB),
      confirmationCode("ffeeddccbbaa99887766554433221100", AB, CD),
    ]);

    expect(codes).toEqual(["92Q-M2H", "9MX-3B9", "8VG-KBV"]);
  });

  it("sdp fingerprint is read from the sha-256 line in upper case", () => {
    const sdp = ["v=0", "a=ice-ufrag:abcd", `a=fingerprint:sha-256 ${AB.toLowerCase()}`, "a=setup:actpass", ""].join(
      "\r\n",
    );

    expect(sdpFingerprint(sdp)).toBe(AB);
  });

  it("sdp without a sha-256 fingerprint has no fingerprint", () => {
    expect(sdpFingerprint("v=0\r\na=fingerprint:sha-1 AA:BB\r\n")).toBeNull();
  });
});
