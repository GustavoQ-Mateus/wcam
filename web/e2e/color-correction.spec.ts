import { expect, test } from "@playwright/test";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { endSession, goLive, status, waitForColorCorrection } from "./session-helpers";

const CORRECTION_TIMEOUT_MS = 10_000;
const FAKE_CAMERA_TRANSFER = "smpte170m";

test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
});

test("the fake camera declares its color space and a standard display keeps the default color", async ({
  page,
  request,
}) => {
  await goLive(page, request);

  const correction = await waitForColorCorrection(request, CORRECTION_TIMEOUT_MS);
  const colorSpace = (await status(request)).session?.cameraCapabilities?.colorSpace;
  console.log(`color space ${JSON.stringify(colorSpace)}, correction ${JSON.stringify(correction)}`);

  expect(colorSpace?.transfer).toBe(FAKE_CAMERA_TRANSFER);
  expect(correction).toEqual({ state: "default", transfer: FAKE_CAMERA_TRANSFER, display: "standard" });
});
