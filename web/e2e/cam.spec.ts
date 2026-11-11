import { expect, test, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { camUrl, PHONE_LANDSCAPE, PHONE_PORTRAIT, turnOnCamera } from "./cam-helpers";
import { consoleUrl, endSession, goLive } from "./session-helpers";

const CONSOLE_CHUNK_NAME = "console-page";
const PORTRAIT_FRAME = { width: 1080, height: 1920 };
const UNUSED_FRAGMENT = "#t=never-sent";
const DEFAULT_FORMAT = "1080p30";
const STEADY_PHONE_MS = 3000;

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
    await expect(page.getByRole("button", { name: translate("en", "cam.switch_camera") })).toBeVisible();
  });

  test("an upright phone whose camera rotates by itself stays upright without reapplying", async ({
    page,
    request,
  }) => {
    await page.addInitScript((frame) => {
      const calls: string[] = [];
      const flips: string[] = [];
      Object.assign(window, { formatCalls: calls, layoutFlips: flips });
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
        if (track) {
          track.applyConstraints = (constraints?: MediaTrackConstraints) => {
            const exact = (value: unknown) =>
              typeof value === "object" && value !== null && "exact" in value ? Number(value.exact) : null;
            const width = exact(constraints?.width) ?? canvas.width;
            const height = exact(constraints?.height) ?? canvas.height;
            calls.push(`${String(width)}x${String(height)}`);
            canvas.width = Math.min(width, height);
            canvas.height = Math.max(width, height);
            return Promise.resolve();
          };
          track.getSettings = () => ({ width: canvas.width, height: canvas.height, frameRate: 30 });
        }
        return Promise.resolve(stream);
      };
      new MutationObserver(() => {
        const portrait = document.querySelector("main")?.dataset.portrait ?? "";
        if (flips.at(-1) !== portrait) {
          flips.push(portrait);
        }
      }).observe(document, { attributes: true, subtree: true, attributeFilter: ["data-portrait"] });
    }, PORTRAIT_FRAME);

    await goLive(page, request);
    await page.waitForTimeout(STEADY_PHONE_MS);
    const settled = await readRotationLog(page);
    await page.waitForTimeout(STEADY_PHONE_MS);

    const later = await readRotationLog(page);
    expect(later).toEqual(settled);
    expect(later.flips.at(-1)).toBe("true");
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

function readRotationLog(page: Page): Promise<{ calls: number; flips: string[] }> {
  return page.evaluate(() => {
    const state = window as unknown as { formatCalls: string[]; layoutFlips: string[] };
    return { calls: state.formatCalls.length, flips: [...state.layoutFlips] };
  });
}
