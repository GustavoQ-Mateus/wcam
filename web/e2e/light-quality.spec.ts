import { expect, test } from "@playwright/test";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { requiredUrl } from "./environment";
import { consoleUrl, endSession, goLive, NO_CONTENT_STATUS, status } from "./session-helpers";

const LIGHT_BITRATE_LIMIT_KBPS = 5_500;
const LIGHT_TIMEOUT_MS = 5_000;
const BALANCED_TIMEOUT_MS = 30_000;

test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
  await request.put(consoleUrl("/api/quality-preset"), { data: { preset: "balanced" } });
});

test("after switching to light the measured bitrate drops below 5500 kbps within 5 s", async ({ page, request }) => {
  test.setTimeout(BALANCED_TIMEOUT_MS * 2);
  requiredUrl("E2E_QUALITY_REFERENCE");
  await goLive(page, request);
  await expect
    .poll(async () => (await status(request)).session?.video?.bitrateKbps ?? 0, { timeout: BALANCED_TIMEOUT_MS })
    .toBeGreaterThan(LIGHT_BITRATE_LIMIT_KBPS);
  const before = (await status(request)).session?.video?.bitrateKbps ?? 0;

  const response = await request.put(consoleUrl("/api/quality-preset"), { data: { preset: "light" } });
  expect(response.status()).toBe(NO_CONTENT_STATUS);

  await expect
    .poll(async () => (await status(request)).session?.video?.bitrateKbps ?? Infinity, { timeout: LIGHT_TIMEOUT_MS })
    .toBeLessThan(LIGHT_BITRATE_LIMIT_KBPS);
  const measured = JSON.stringify({
    beforeKbps: before,
    afterKbps: (await status(request)).session?.video?.bitrateKbps ?? 0,
  });
  test.info().annotations.push({ type: "bitrate", description: measured });
  console.log(`bitrate ${measured}`);
});
