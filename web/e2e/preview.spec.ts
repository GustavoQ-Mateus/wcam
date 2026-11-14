import { expect, test, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { requiredUrl } from "./environment";
import { endSession, goLive } from "./session-helpers";

const PREVIEW_WIDTH = 960;
const PREVIEW_TIMEOUT_MS = 10_000;
const NO_CONTENT_STATUS = 204;

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
});

function previewWidth(consolePage: Page): Promise<number> {
  return consolePage.evaluate(() => document.querySelector<HTMLVideoElement>("main video")?.videoWidth ?? 0);
}

test("the console preview shows the picture the apps receive", async ({ page, request }) => {
  await goLive(page, request);
  const consolePage = await page.context().newPage();
  await consolePage.goto(requiredUrl("E2E_CONSOLE_URL"));

  await expect(consolePage.getByText(translate("en", "console.preview_label"))).toBeVisible({
    timeout: PREVIEW_TIMEOUT_MS,
  });
  await expect.poll(() => previewWidth(consolePage), { timeout: PREVIEW_TIMEOUT_MS }).toBe(PREVIEW_WIDTH);
});

test("turning the preview off closes its connection and keeps the phone live", async ({ page, request }) => {
  await goLive(page, request);
  const consolePage = await page.context().newPage();
  await consolePage.goto(requiredUrl("E2E_CONSOLE_URL"));
  await expect.poll(() => previewWidth(consolePage), { timeout: PREVIEW_TIMEOUT_MS }).toBe(PREVIEW_WIDTH);
  const closed = consolePage.waitForResponse(
    (response) => response.url().endsWith("/api/preview") && response.request().method() === "DELETE",
  );

  await consolePage.getByRole("button", { name: translate("en", "controls.preview_off") }).click();

  expect((await closed).status()).toBe(NO_CONTENT_STATUS);
  await expect(consolePage.getByText(translate("en", "console.preview_hidden"))).toBeVisible();
  await expect(consolePage.locator("main video")).toHaveCount(0);
  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible();
});
