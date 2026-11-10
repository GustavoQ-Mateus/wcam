import { expect, test } from "@playwright/test";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { requiredUrl } from "./environment";
import { consoleUrl, endSession, goLive, NO_CONTENT_STATUS, status } from "./session-helpers";

const SMALL_FORMAT_BITRATE_LIMIT_KBPS = 5_500;
const SMALL_FORMAT_TIMEOUT_MS = 5_000;
const DEFAULT_FORMAT_TIMEOUT_MS = 30_000;

test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
  await request.put(consoleUrl("/api/video-format"), { data: { format: "1080p30" } });
});

test("after switching to 720p30 the measured bitrate drops below 5500 kbps within 5 s", async ({ page, request }) => {
  test.setTimeout(DEFAULT_FORMAT_TIMEOUT_MS * 2);
  requiredUrl("E2E_QUALITY_REFERENCE");
  await goLive(page, request);
  await expect
    .poll(async () => (await status(request)).session?.video?.bitrateKbps ?? 0, { timeout: DEFAULT_FORMAT_TIMEOUT_MS })
    .toBeGreaterThan(SMALL_FORMAT_BITRATE_LIMIT_KBPS);
  const before = (await status(request)).session?.video?.bitrateKbps ?? 0;

  const response = await request.put(consoleUrl("/api/video-format"), { data: { format: "720p30" } });
  expect(response.status()).toBe(NO_CONTENT_STATUS);

  await expect
    .poll(async () => (await status(request)).session?.video?.bitrateKbps ?? Infinity, {
      timeout: SMALL_FORMAT_TIMEOUT_MS,
    })
    .toBeLessThan(SMALL_FORMAT_BITRATE_LIMIT_KBPS);
  const measured = JSON.stringify({
    beforeKbps: before,
    afterKbps: (await status(request)).session?.video?.bitrateKbps ?? 0,
  });
  test.info().annotations.push({ type: "bitrate", description: measured });
  console.log(`bitrate ${measured}`);
});
