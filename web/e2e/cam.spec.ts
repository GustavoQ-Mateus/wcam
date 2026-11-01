import { expect, test, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { requiredUrl } from "./environment";

const CONSOLE_CHUNK_NAME = "console-page";
const PHONE_LANDSCAPE = { width: 844, height: 390 };
const PHONE_PORTRAIT = { width: 390, height: 844 };
const PORTRAIT_FRAME = { width: 720, height: 1280 };

test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

function camUrl(fragment = ""): string {
  return `${requiredUrl("E2E_PHONE_URL")}/cam${fragment}`;
}

async function turnOnCamera(page: Page): Promise<void> {
  await page.goto(camUrl("#t=teste"));
  await page.getByRole("button", { name: translate("en", "cam.intro_action") }).click();
}

async function liveTrackSettings(
  page: Page,
): Promise<{ readyState: string; width: number; height: number; fps: number }> {
  return page.evaluate(() => {
    const stream = document.querySelector("video")?.srcObject;
    const track = stream instanceof MediaStream ? stream.getVideoTracks()[0] : undefined;
    const settings = track?.getSettings() ?? {};
    return {
      readyState: track?.readyState ?? "missing",
      width: settings.width ?? 0,
      height: settings.height ?? 0,
      fps: Math.round(settings.frameRate ?? 0),
    };
  });
}

test("cam page opens over https and shows missing pairing without fragment", async ({ page }) => {
  const response = await page.goto(camUrl());

  expect(response?.url()).toMatch(/^https:/);
  await expect(page.getByText(translate("en", "cam.missing_pairing"))).toBeVisible();
});

test("cam page does not load the console chunk", async ({ page }) => {
  const requestedUrls: string[] = [];
  page.on("request", (request) => requestedUrls.push(request.url()));

  await page.goto(camUrl(), { waitUntil: "networkidle" });
  await expect(page.getByText(translate("en", "cam.missing_pairing"))).toBeVisible();

  expect(requestedUrls.filter((url) => url.includes(CONSOLE_CHUNK_NAME))).toEqual([]);
});

test("cam in landscape reaches ready with the capture format and no fragment in the address", async ({ page }) => {
  await turnOnCamera(page);

  await expect(page.getByRole("button", { name: translate("en", "cam.switch_camera") })).toBeVisible();
  const settings = await liveTrackSettings(page);
  const format = translate("en", "cam.capture_format", {
    width: String(settings.width),
    height: String(settings.height),
    fps: String(settings.fps),
  });
  await expect(page.getByText(format)).toBeVisible();
  expect(new URL(page.url()).hash).toBe("");
});

test.describe("in portrait", () => {
  test.use({ viewport: PHONE_PORTRAIT });

  test("cam with a portrait frame shows rotate", async ({ page }) => {
    await page.addInitScript((frame) => {
      navigator.mediaDevices.getUserMedia = () => {
        const canvas = document.createElement("canvas");
        canvas.width = frame.width;
        canvas.height = frame.height;
        const context = canvas.getContext("2d");
        const paint = () => {
          context?.fillRect(0, 0, canvas.width, canvas.height);
          requestAnimationFrame(paint);
        };
        paint();
        return Promise.resolve(canvas.captureStream());
      };
    }, PORTRAIT_FRAME);

    await turnOnCamera(page);

    await expect(page.getByText(translate("en", "cam.rotate_title"))).toBeVisible();
    await expect(page.getByRole("button", { name: translate("en", "cam.switch_camera") })).toHaveCount(0);
  });
});

test("cam shows denied when the permission is refused", async ({ page }) => {
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () =>
      Promise.reject(new DOMException("Permission denied", "NotAllowedError"));
  });

  await turnOnCamera(page);

  await expect(page.getByText(translate("en", "cam.denied_title"))).toBeVisible();
  await expect(page.getByRole("button", { name: translate("en", "cam.retry") })).toBeVisible();
});

test("turning the preview off shows preview_off and keeps the track live", async ({ page }) => {
  await turnOnCamera(page);

  await page.getByRole("button", { name: translate("en", "cam.preview_off") }).click();

  await expect(page.getByText(translate("en", "cam.preview_hidden"))).toBeVisible();
  expect((await liveTrackSettings(page)).readyState).toBe("live");
});
