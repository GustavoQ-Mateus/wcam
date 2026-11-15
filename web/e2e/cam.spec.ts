import { expect, test, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { camUrl, PHONE_LANDSCAPE, PHONE_PORTRAIT, turnOnCamera } from "./cam-helpers";
import { consoleUrl, endSession, goLive } from "./session-helpers";

const CONSOLE_CHUNK_NAME = "console-page";
const PORTRAIT_FRAME = { width: 1080, height: 1920 };
const UNUSED_FRAGMENT = "#t=never-sent";
const DEFAULT_FORMAT = "1080p30";
const STEADY_PHONE_MS = 2500;
const ROTATION_DELAY_MS = 300;
const TURN_TIMEOUT_MS = 5000;
const MAXIMUM_REQUESTS_PER_TURN = 2;

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

  test.afterEach(async ({ request }) => {
    await endSession(request);
    await request.put(consoleUrl("/api/video-format"), { data: { format: DEFAULT_FORMAT } });
  });

  test("an upright phone goes live with the portrait hint and its controls", async ({ page, request }) => {
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

    await goLive(page, request);

    await expect(page.getByText(translate("en", "cam.portrait_hint"))).toBeVisible();
    await expect(page.getByRole("button", { name: translate("en", "controls.switch_camera") })).toBeVisible();
  });

  test("turning the phone upright, lying down and upright again ends each turn matching the screen", async ({
    page,
    request,
  }) => {
    await page.addInitScript(
      ({ frame, delay }) => {
        const calls: string[] = [];
        Object.assign(window, { formatCalls: calls });
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
          const stream = canvas.captureStream();
          const track = stream.getVideoTracks()[0];
          let lastRequest = "";
          if (track) {
            track.applyConstraints = (constraints?: MediaTrackConstraints) => {
              const exact = (value: unknown) =>
                typeof value === "object" && value !== null && "exact" in value ? Number(value.exact) : null;
              const width = exact(constraints?.width) ?? canvas.width;
              const height = exact(constraints?.height) ?? canvas.height;
              const request = `${String(width)}x${String(height)}`;
              calls.push(request);
              if (request !== lastRequest) {
                lastRequest = request;
                const devicePortrait = window.matchMedia("(orientation: portrait)").matches;
                window.setTimeout(() => {
                  canvas.width = devicePortrait ? height : width;
                  canvas.height = devicePortrait ? width : height;
                }, delay);
              }
              return Promise.resolve();
            };
            track.getSettings = () => ({ width: canvas.width, height: canvas.height, frameRate: 30 });
          }
          return Promise.resolve(stream);
        };
      },
      { frame: PORTRAIT_FRAME, delay: ROTATION_DELAY_MS },
    );

    await goLive(page, request);
    const upright = await settledTurn(page, true);
    await page.setViewportSize(PHONE_LANDSCAPE);
    const lyingDown = await settledTurn(page, false);
    await page.setViewportSize(PHONE_PORTRAIT);
    const uprightAgain = await settledTurn(page, true);

    expect([upright.portrait, lyingDown.portrait, uprightAgain.portrait]).toEqual([true, false, true]);
    expect(Math.max(lyingDown.calls - upright.calls, uprightAgain.calls - lyingDown.calls)).toBeLessThanOrEqual(
      MAXIMUM_REQUESTS_PER_TURN,
    );
    await expect(page.getByText(translate("en", "cam.portrait_hint"))).toBeVisible();
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

async function settledTurn(page: Page, screenPortrait: boolean): Promise<{ portrait: boolean; calls: number }> {
  await expect(page.locator("main")).toHaveAttribute("data-portrait", String(screenPortrait));
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const video = document.querySelector("video");
          return video ? video.videoHeight > video.videoWidth : null;
        }),
      { timeout: TURN_TIMEOUT_MS },
    )
    .toBe(screenPortrait);
  await page.waitForTimeout(STEADY_PHONE_MS);
  return page.evaluate(() => {
    const video = document.querySelector("video");
    const calls = (window as unknown as { formatCalls: string[] }).formatCalls.length;
    return { portrait: video ? video.videoHeight > video.videoWidth : false, calls };
  });
}
