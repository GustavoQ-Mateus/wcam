import { expect, test } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE, trackSettings, turnOnCamera } from "./cam-helpers";
import { consoleUrl, endSession, goLive, NO_CONTENT_STATUS, reachConfirmation, status } from "./session-helpers";

const VIDEO_TIMEOUT_MS = 20_000;
const SOURCE_TIMEOUT_MS = 5_000;

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
});

test("phone and computer show the same code and the phone goes live after confirmation", async ({ page, request }) => {
  await reachConfirmation(page, request);
  expect(new URL(page.url()).hash).toBe("");
  expect((await status(request)).virtualCamera.source).toBe("placeholder");

  expect((await request.post(consoleUrl("/api/sessions/current/confirm"))).status()).toBe(NO_CONTENT_STATUS);

  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible();
  const settings = await trackSettings(page);
  const format = translate("en", "cam.capture_format", {
    width: String(settings.width),
    height: String(settings.height),
    fps: String(settings.fps),
  });
  await expect(page.getByText(format)).toBeVisible();
  await expect
    .poll(async () => (await status(request)).session?.video ?? null, { timeout: VIDEO_TIMEOUT_MS })
    .not.toBeNull();
  await expect
    .poll(async () => (await status(request)).virtualCamera.source, { timeout: SOURCE_TIMEOUT_MS })
    .toBe("phone");

  await endSession(request);

  await expect
    .poll(async () => (await status(request)).virtualCamera.source, { timeout: SOURCE_TIMEOUT_MS })
    .toBe("placeholder");
});

test("turning the preview off while live keeps the track live and the tally on", async ({ page, request }) => {
  await goLive(page, request);

  await page.getByRole("button", { name: translate("en", "cam.preview_off") }).click();

  await expect(page.getByText(translate("en", "cam.preview_hidden"))).toBeVisible();
  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible();
  expect((await trackSettings(page)).readyState).toBe("live");
});

test("a used pairing token shows pairing_failed", async ({ page, request }) => {
  const fragment = await reachConfirmation(page, request);
  await endSession(request);

  const secondPage = await page.context().newPage();
  await turnOnCamera(secondPage, fragment);

  await expect(secondPage.getByText(translate("en", "cam.pairing_failed"))).toBeVisible();
});

test("rejecting on the computer shows ended on the phone", async ({ page, request }) => {
  await reachConfirmation(page, request);

  expect((await request.post(consoleUrl("/api/sessions/current/reject"))).status()).toBe(NO_CONTENT_STATUS);

  await expect(page.getByText(translate("en", "cam.ended_rejected"))).toBeVisible();
});
