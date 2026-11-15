import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { requiredUrl } from "./environment";
import { consoleUrl, endSession, status } from "./session-helpers";

const VIDEO_WIDTH = 1280;
const VIDEO_HEIGHT = 720;
const VIDEO_DURATION_SECONDS = 6;
const CONFLICT_STATUS = 409;
const UPLOAD_TIMEOUT_MS = 30_000;
const PREVIEW_TIMEOUT_MS = 10_000;
const POSITION_TIMEOUT_MS = 5_000;
const DRAG_START_FRACTION = 0.5;
const EARLY_TARGET_FRACTION = 0.25;
const LATE_TARGET_FRACTION = 0.75;
const POSITION_TOLERANCE_SECONDS = 0.5;

test.describe.configure({ mode: "serial" });

async function clearVideo(request: APIRequestContext): Promise<void> {
  await request.put(consoleUrl("/api/video-source"), { data: { active: false } });
  await request.delete(consoleUrl("/api/video-source/file"));
}

async function previewWidth(page: Page): Promise<number> {
  return page.evaluate(() => document.querySelector<HTMLVideoElement>("main video")?.videoWidth ?? 0);
}

async function dragTimeline(page: Page, fromFraction: number, toFraction: number): Promise<void> {
  const slider = page.getByRole("slider", { name: translate("en", "console.video_timeline") });
  const box = await slider.boundingBox();
  if (!box) {
    throw new Error("Timeline is not visible");
  }
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + box.width * fromFraction, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * toFraction, y, { steps: 5 });
  await page.mouse.up();
}

test.beforeAll(async ({ request }) => {
  await endSession(request);
  await clearVideo(request);
});

test.afterAll(async ({ request }) => {
  await clearVideo(request);
});

test("a video sent from the console loops on the camera, jumps on the timeline and gives way to the phone", async ({
  page,
  request,
}) => {
  await page.goto(requiredUrl("E2E_CONSOLE_URL"));
  await expect(page.getByRole("status")).toHaveText(translate("en", "state.waiting"));

  await page.locator('input[type="file"]').setInputFiles(requiredUrl("E2E_TEST_VIDEO"));
  const useVideo = page.getByRole("button", { name: translate("en", "controls.use_video") });
  await expect(useVideo).toBeVisible({ timeout: UPLOAD_TIMEOUT_MS });
  const file = (await status(request)).videoSource.file;
  expect(file).toMatchObject({ width: VIDEO_WIDTH, height: VIDEO_HEIGHT, codec: "h264" });
  expect(file?.durationSeconds).toBeCloseTo(VIDEO_DURATION_SECONDS, 0);

  await useVideo.click();
  await expect(page.getByRole("status")).toHaveText(translate("en", "state.video"));
  await expect.poll(async () => (await status(request)).virtualCamera.source).toBe("video");
  await expect(page.getByRole("img", { name: translate("en", "console.pairing_title") })).toHaveCount(0);
  await expect.poll(() => previewWidth(page), { timeout: PREVIEW_TIMEOUT_MS }).toBeGreaterThan(0);
  expect((await request.post(consoleUrl("/api/pairing"))).status()).toBe(CONFLICT_STATUS);

  await page.getByRole("button", { name: translate("en", "controls.freeze") }).click();
  await expect.poll(async () => (await status(request)).controls.frozen).toBe(true);
  const frozenAt = (await status(request)).videoSource.positionSeconds ?? 0;
  const targetFraction = frozenAt < VIDEO_DURATION_SECONDS / 2 ? LATE_TARGET_FRACTION : EARLY_TARGET_FRACTION;
  await dragTimeline(page, DRAG_START_FRACTION, targetFraction);
  const chosenSeconds = (file?.durationSeconds ?? VIDEO_DURATION_SECONDS) * targetFraction;
  await expect
    .poll(
      async () => {
        const position = (await status(request)).videoSource.positionSeconds ?? -1;
        return Math.abs(position - chosenSeconds) < POSITION_TOLERANCE_SECONDS;
      },
      { timeout: POSITION_TIMEOUT_MS },
    )
    .toBe(true);
  await page
    .getByRole("button", { name: translate("en", "controls.unfreeze") })
    .first()
    .click();
  await expect.poll(async () => (await status(request)).controls.frozen).toBe(false);

  await page.getByRole("button", { name: translate("en", "controls.back_to_phone") }).click();
  await expect(page.getByRole("status")).toHaveText(translate("en", "state.waiting"));
  await expect.poll(async () => (await status(request)).virtualCamera.source).not.toBe("video");
  await page.getByRole("button", { name: translate("en", "console.pairing_new") }).click();
  await expect(page.getByRole("img", { name: translate("en", "console.pairing_title") })).toBeVisible();
});
