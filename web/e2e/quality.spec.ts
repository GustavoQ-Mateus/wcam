import { expect, test } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { requiredUrl } from "./environment";
import { endSession, goLive, status, waitForColorCorrection } from "./session-helpers";

const MINIMUM_SSIM = 0.98;
const MINIMUM_FRAMES = 30;
const QUALITY_TIMEOUT_MS = 60_000;
const PREVIEW_TIMEOUT_MS = 10_000;

test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
});

test("frames delivered to the virtual camera keep an ssim of at least 0.98 with the console preview on", async ({
  page,
  request,
}) => {
  test.setTimeout(QUALITY_TIMEOUT_MS * 2);
  requiredUrl("E2E_QUALITY_REFERENCE");

  const consolePage = await page.context().newPage();
  await consolePage.goto(requiredUrl("E2E_CONSOLE_URL"));
  await goLive(page, request);
  await expect(consolePage.getByText(translate("en", "console.preview_label"))).toBeVisible({
    timeout: PREVIEW_TIMEOUT_MS,
  });
  expect((await status(request)).controls.mirror).toBe(false);
  await waitForColorCorrection(request, QUALITY_TIMEOUT_MS);

  await expect
    .poll(async () => (await status(request)).quality?.frames ?? 0, { timeout: QUALITY_TIMEOUT_MS })
    .toBeGreaterThanOrEqual(MINIMUM_FRAMES);
  const { quality, session } = await status(request);
  const measured = JSON.stringify({ quality, video: session?.video ?? null });
  test.info().annotations.push({ type: "quality", description: measured });
  console.log(`quality ${measured}`);

  expect(quality?.ssim ?? 0).toBeGreaterThanOrEqual(MINIMUM_SSIM);
});
