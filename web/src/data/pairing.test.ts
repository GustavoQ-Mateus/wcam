import { describe, expect, it, vi } from "vitest";
import { takePairingToken } from "./pairing";

describe("pairing", () => {
  it("pairing fragment is read and removed from the address", () => {
    const replaceAddress = vi.fn();

    const token = takePairingToken({ pathname: "/cam", search: "", hash: "#t=teste" }, replaceAddress);

    expect(token).toBe("teste");
    expect(replaceAddress).toHaveBeenCalledWith("/cam");
  });

  it("address without pairing fragment is left untouched", () => {
    const replaceAddress = vi.fn();

    const token = takePairingToken({ pathname: "/cam", search: "", hash: "" }, replaceAddress);

    expect(token).toBeNull();
    expect(replaceAddress).not.toHaveBeenCalled();
  });
});
