import { expect, test } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { camUrl, PHONE_LANDSCAPE, PHONE_PORTRAIT, turnOnCamera } from "./cam-helpers";

const CONSOLE_CHUNK_NAME = "console-page";
const PORTRAIT_FRAME = { width: 720, height: 1280 };
const UNUSED_FRAGMENT = "#t=never-sent";

test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

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

    await turnOnCamera(page, UNUSED_FRAGMENT);

    await expect(page.getByText(translate("en", "cam.rotate_title"))).toBeVisible();
    await expect(page.getByRole("button", { name: translate("en", "cam.switch_camera") })).toHaveCount(0);
  });
});

test("cam shows denied when the permission is refused", async ({ page }) => {
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () =>
      Promise.reject(new DOMException("Permission denied", "NotAllowedError"));
  });

  await turnOnCamera(page, UNUSED_FRAGMENT);

  await expect(page.getByText(translate("en", "cam.denied_title"))).toBeVisible();
  await expect(page.getByRole("button", { name: translate("en", "cam.retry") })).toBeVisible();
});
