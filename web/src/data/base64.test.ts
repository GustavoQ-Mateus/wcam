import { describe, expect, it } from "vitest";
import { toBase64 } from "./base64";

describe("toBase64", () => {
  it("encodes bytes longer than one binary chunk without losing any", () => {
    const bytes = Uint8Array.from({ length: 0x8000 + 5 }, (_, index) => index % 256);

    expect([...atob(toBase64(bytes))].map((character) => character.charCodeAt(0))).toEqual([...bytes]);
  });
});
