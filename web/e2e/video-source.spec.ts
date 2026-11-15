import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { requiredUrl } from "./environment";
import { consoleUrl, endSession, goLive, status } from "./session-helpers";

const LANDSCAPE_VIDEO = { width: 1280, height: 720, codec: "h264", durationSeconds: 6 };
const PORTRAIT_VIDEO = { width: 720, height: 1280, durationSeconds: 4 };
const UPLOAD_TIMEOUT_MS = 60_000;
const PREVIEW_TIMEOUT_MS = 10_000;
const POSITION_TIMEOUT_MS = 5_000;
const TRIM_FRACTION = 0.4;
const SEEK_FRACTION = 0.75;
const POSITION_TOLERANCE_SECONDS = 0.5;
const DURATION_TOLERANCE_DIGITS = 0;

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

async function clearVideos(request: APIRequestContext): Promise<void> {
  await request.put(consoleUrl("/api/video-source"), { data: { active: false } });
  for (const video of (await status(request)).videoSource.videos) {
    await request.delete(consoleUrl(`/api/videos/${encodeURIComponent(video.id)}`));
  }
}

async function openConsole(page: Page): Promise<Page> {
  const consolePage = await page.context().newPage();
  await consolePage.setViewportSize({ width: 1440, height: 900 });
  await consolePage.goto(requiredUrl("E2E_CONSOLE_URL"));
  await expect(consolePage.getByRole("status")).toHaveText(translate("en", "state.live"));
  return consolePage;
}

async function center(locator: Locator): Promise<{ x: number; y: number; width: number }> {
  const box = await locator.boundingBox();
  if (!box) {
    throw new Error("Element is not visible");
  }
  return { x: box.x + box.width / 2, y: box.y + box.height / 2, width: box.width };
}

async function drag(page: Page, from: { x: number; y: number }, toX: number): Promise<void> {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(toX, from.y, { steps: 8 });
  await page.mouse.up();
}

async function clipVideoIds(request: APIRequestContext): Promise<string[]> {
  return (await status(request)).videoSource.timeline.clips.map((clip) => clip.videoId);
}

function clip(consolePage: Page, index: number, count: number): Locator {
  return consolePage.getByRole("button", { name: new RegExp(`^Clip ${String(index)} of ${String(count)}:`) });
}

async function previewWidth(page: Page): Promise<number> {
  return page.evaluate(() => document.querySelector<HTMLVideoElement>("main video")?.videoWidth ?? 0);
}

test.beforeAll(async ({ request }) => {
  await endSession(request);
  await clearVideos(request);
});

test.afterAll(async ({ request }) => {
  await clearVideos(request);
  await endSession(request);
});

test("two videos edited on the timeline loop on the camera while the phone stays connected", async ({
  page,
  request,
}) => {
  await goLive(page, request);
  const sessionId = (await status(request)).session?.id;
  const consolePage = await openConsole(page);
  await consolePage.getByRole("button", { name: translate("en", "controls.use_video") }).click();
  await expect(consolePage.getByRole("heading", { name: translate("en", "console.video_library") })).toBeVisible();

  await consolePage
    .locator('input[type="file"]')
    .setInputFiles([requiredUrl("E2E_TEST_VIDEO"), requiredUrl("E2E_TEST_VIDEO_2")]);
  await expect
    .poll(async () => (await status(request)).videoSource.videos.length, { timeout: UPLOAD_TIMEOUT_MS })
    .toBe(2);
  const [landscape, portrait] = (await status(request)).videoSource.videos;
  expect(landscape).toMatchObject({ width: LANDSCAPE_VIDEO.width, height: LANDSCAPE_VIDEO.height, codec: "h264" });
  expect(landscape?.durationSeconds).toBeCloseTo(LANDSCAPE_VIDEO.durationSeconds, DURATION_TOLERANCE_DIGITS);
  expect(portrait).toMatchObject({ width: PORTRAIT_VIDEO.width, height: PORTRAIT_VIDEO.height });

  const addButtons = consolePage.getByRole("button", { name: translate("en", "console.video_add") });
  await addButtons.nth(0).click();
  await expect.poll(() => clipVideoIds(request)).toHaveLength(1);
  await addButtons.nth(1).click();
  await expect.poll(() => clipVideoIds(request)).toEqual([landscape?.id, portrait?.id]);

  await clip(consolePage, 1, 2).click();
  const trimEnd = consolePage.getByRole("slider", {
    name: translate("en", "console.timeline_trim_end", { index: "1" }),
  });
  const firstClip = await center(clip(consolePage, 1, 2));
  const edge = await center(trimEnd);
  await drag(consolePage, edge, edge.x - firstClip.width * TRIM_FRACTION);
  await expect
    .poll(
      async () => (await status(request)).videoSource.timeline.clips[0]?.outSeconds ?? LANDSCAPE_VIDEO.durationSeconds,
    )
    .toBeLessThan(LANDSCAPE_VIDEO.durationSeconds - 1);

  const secondClip = await center(clip(consolePage, 2, 2));
  const trimmedFirst = await center(clip(consolePage, 1, 2));
  await drag(consolePage, secondClip, trimmedFirst.x - trimmedFirst.width / 2);
  await expect.poll(() => clipVideoIds(request)).toEqual([portrait?.id, landscape?.id]);

  const ruler = consolePage.getByRole("slider", { name: translate("en", "console.timeline_playhead") });
  const rulerBox = await ruler.boundingBox();
  const portraitClip = await center(clip(consolePage, 1, 2));
  await consolePage.mouse.click(portraitClip.x, (rulerBox?.y ?? 0) + (rulerBox?.height ?? 0) / 2);
  await consolePage.getByRole("button", { name: translate("en", "console.timeline_split") }).click();
  await expect.poll(() => clipVideoIds(request)).toEqual([portrait?.id, portrait?.id, landscape?.id]);
  await clip(consolePage, 2, 3).focus();
  await consolePage.keyboard.press("Delete");
  await expect.poll(() => clipVideoIds(request)).toEqual([portrait?.id, landscape?.id]);

  await consolePage.getByRole("button", { name: translate("en", "controls.use_video") }).click();
  await expect(consolePage.getByRole("status")).toHaveText(translate("en", "state.video"));
  await expect.poll(async () => (await status(request)).virtualCamera.source).toBe("video");
  expect((await status(request)).session).toMatchObject({ id: sessionId, state: "live" });
  await expect(page.getByText(translate("en", "cam.video_playing"))).toBeVisible();
  await expect.poll(() => previewWidth(consolePage), { timeout: PREVIEW_TIMEOUT_MS }).toBeGreaterThan(0);

  await consolePage.getByRole("button", { name: translate("en", "console.timeline_pause") }).click();
  await expect.poll(async () => (await status(request)).controls.frozen).toBe(true);
  const box = await ruler.boundingBox();
  const timelineDuration = (await status(request)).videoSource.timeline.durationSeconds;
  if (!box) {
    throw new Error("Ruler is not visible");
  }
  await drag(consolePage, { x: box.x + box.width / 2, y: box.y + box.height / 2 }, box.x + box.width * SEEK_FRACTION);
  await expect
    .poll(
      async () => {
        const position = (await status(request)).videoSource.positionSeconds ?? -1;
        return Math.abs(position - timelineDuration * SEEK_FRACTION) < POSITION_TOLERANCE_SECONDS;
      },
      { timeout: POSITION_TIMEOUT_MS },
    )
    .toBe(true);
  await consolePage.getByRole("button", { name: translate("en", "console.timeline_play") }).click();
  await expect.poll(async () => (await status(request)).controls.frozen).toBe(false);

  await page.getByRole("button", { name: translate("en", "cam.back_to_camera") }).click();
  await expect.poll(async () => (await status(request)).videoSource.active).toBe(false);
  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible();
  await expect(consolePage.getByRole("status")).toHaveText(translate("en", "state.live"));
  await expect.poll(async () => (await status(request)).virtualCamera.source).toBe("phone");
  expect((await status(request)).session?.id).toBe(sessionId);

  await consolePage.getByRole("button", { name: translate("en", "controls.use_video") }).click();
  await expect(consolePage.getByRole("heading", { name: translate("en", "console.video_library") })).toBeVisible();
  await consolePage.getByRole("button", { name: translate("en", "controls.use_video") }).click();
  await expect(consolePage.getByRole("status")).toHaveText(translate("en", "state.video"));
  await consolePage.getByRole("button", { name: translate("en", "controls.back_to_phone") }).click();
  await expect(consolePage.getByRole("status")).toHaveText(translate("en", "state.live"));
  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible();
});
