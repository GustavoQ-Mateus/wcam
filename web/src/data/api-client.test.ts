import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, changeQualityPreset, requestJson, uploadComparisonPc, uploadComparisonScreen } from "./api-client";

const FORBIDDEN_STATUS = 403;
const NO_CONTENT_STATUS = 204;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("api client turns error body into ApiError with code", async () => {
    const body = { error: { code: "not_same_network", message: "The request does not come from the local network." } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(body, { status: FORBIDDEN_STATUS })));

    const error = await requestJson("/api/health").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "not_same_network", status: FORBIDDEN_STATUS });
  });

  it("network failure becomes ApiError with network_error code", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(requestJson("/api/health")).rejects.toMatchObject({ code: "network_error" });
  });

  it("quality preset change is a PUT with the preset in the body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: NO_CONTENT_STATUS }));
    vi.stubGlobal("fetch", fetchMock);

    await changeQualityPreset({ preset: "light" });

    expect(fetchMock).toHaveBeenCalledWith("/api/quality-preset", {
      method: "PUT",
      body: '{"preset":"light"}',
      headers: { "Content-Type": "application/json" },
    });
  });

  it("comparison image is sent as png to its comparison", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: NO_CONTENT_STATUS }));
    vi.stubGlobal("fetch", fetchMock);
    const png = new Blob([new Uint8Array([137, 80, 78, 71])], { type: "image/png" });

    await uploadComparisonScreen("c 1", png);

    expect(fetchMock).toHaveBeenCalledWith("/api/dev/comparisons/c%201/screen", {
      method: "PUT",
      body: png,
      headers: { "Content-Type": "image/png" },
    });
  });

  it("computer image is sent with the capture instant of the computer clock", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: NO_CONTENT_STATUS }));
    vi.stubGlobal("fetch", fetchMock);
    const png = new Blob([new Uint8Array([137, 80, 78, 71])], { type: "image/png" });

    await uploadComparisonPc("c1", png, 1794100532634.6);

    expect(fetchMock).toHaveBeenCalledWith("/api/dev/comparisons/c1/pc?capturedAt=1794100532635", {
      method: "PUT",
      body: png,
      headers: { "Content-Type": "image/png" },
    });
  });
});
