import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import type { PairingWindow, Status } from "../src/data/contract";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE, trackSettings, turnOnCamera } from "./cam-helpers";
import { requiredUrl } from "./environment";

const CREATED_STATUS = 201;
const NO_CONTENT_STATUS = 204;
const VIDEO_TIMEOUT_MS = 20_000;

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await request.delete(consoleUrl("/api/sessions/current"));
});

function consoleUrl(path: string): string {
  return `${requiredUrl("E2E_CONSOLE_URL")}${path}`;
}

async function status(request: APIRequestContext): Promise<Status> {
  return (await (await request.get(consoleUrl("/api/status"))).json()) as Status;
}

async function pairingFragment(request: APIRequestContext): Promise<string> {
  const response = await request.post(consoleUrl("/api/pairing"));
  expect(response.status()).toBe(CREATED_STATUS);
  return new URL(((await response.json()) as PairingWindow).url).hash;
}

async function reachConfirmation(page: Page, request: APIRequestContext): Promise<string> {
  const fragment = await pairingFragment(request);
  await turnOnCamera(page, fragment);
  await expect(page.getByText(translate("en", "cam.confirm_title"))).toBeVisible();
  const code = (await status(request)).session?.confirmationCode ?? "";
  expect(code).not.toBe("");
  await expect(page.locator("main")).toContainText(code);
  return fragment;
}

test("phone and computer show the same code and the phone goes live after confirmation", async ({ page, request }) => {
  await reachConfirmation(page, request);
  expect(new URL(page.url()).hash).toBe("");

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
});

test("turning the preview off while live keeps the track live and the tally on", async ({ page, request }) => {
  await reachConfirmation(page, request);
  await request.post(consoleUrl("/api/sessions/current/confirm"));
  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible();

  await page.getByRole("button", { name: translate("en", "cam.preview_off") }).click();

  await expect(page.getByText(translate("en", "cam.preview_hidden"))).toBeVisible();
  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible();
  expect((await trackSettings(page)).readyState).toBe("live");
});

test("a used pairing token shows pairing_failed", async ({ page, request }) => {
  const fragment = await reachConfirmation(page, request);
  await request.delete(consoleUrl("/api/sessions/current"));

  const secondPage = await page.context().newPage();
  await turnOnCamera(secondPage, fragment);

  await expect(secondPage.getByText(translate("en", "cam.pairing_failed"))).toBeVisible();
});

test("rejecting on the computer shows ended on the phone", async ({ page, request }) => {
  await reachConfirmation(page, request);

  expect((await request.post(consoleUrl("/api/sessions/current/reject"))).status()).toBe(NO_CONTENT_STATUS);

  await expect(page.getByText(translate("en", "cam.ended_rejected"))).toBeVisible();
});
