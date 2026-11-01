import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, requestJson } from "./api-client";

const FORBIDDEN_STATUS = 403;

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
});
