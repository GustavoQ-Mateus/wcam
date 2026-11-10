import { expect, test, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { resolutionKey, type Resolution, type VideoFormat } from "../src/data/video-format";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { consoleUrl, endSession, goLive, NO_CONTENT_STATUS, status } from "./session-helpers";

const MAXIMUM_SYNC_MS = 300;
const SIZE_FOLLOWS_MS = 3_000;
const INVALID_REQUEST_STATUS = 422;
const DEFAULT_FORMAT = "1080p30";
const SMALL_FORMAT = { key: "720p30", resolution: "720p", width: 1280, height: 720 } as const;
const TABLE_FORMATS: VideoFormat[] = ["720p30", "720p60", "1080p30", "1440p30", "2160p30"];

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
  await request.put(consoleUrl("/api/video-format"), { data: { format: DEFAULT_FORMAT } });
});

test("a resolution chosen on the phone shows on the console in under 300 ms", async ({ page, request }) => {
  await goLive(page, request);
  await expect.poll(async () => (await status(request)).videoFormat.available).toContain(SMALL_FORMAT.key);
  const consolePage = await openConsole(page);
  await page.getByRole("button", { name: translate("en", "format.label") }).click();
  await recordClick(page);

  const checkedAt = whenChecked(consolePage, SMALL_FORMAT.resolution);
  await page.getByText(translate("en", resolutionKey(SMALL_FORMAT.resolution)), { exact: true }).click();

  expect((await checkedAt) - (await clickedAt(page))).toBeLessThan(MAXIMUM_SYNC_MS);
  expect((await status(request)).videoFormat.selected).toBe(SMALL_FORMAT.key);
});

test("a resolution chosen on the console shows on the phone in under 300 ms", async ({ page, request }) => {
  await goLive(page, request);
  await expect.poll(async () => (await status(request)).videoFormat.available).toContain(SMALL_FORMAT.key);
  const consolePage = await openConsole(page);
  await page.getByRole("button", { name: translate("en", "format.label") }).click();
  await recordClick(consolePage);

  const checkedAt = whenChecked(page, SMALL_FORMAT.resolution);
  await consolePage.getByText(translate("en", resolutionKey(SMALL_FORMAT.resolution)), { exact: true }).click();

  expect((await checkedAt) - (await clickedAt(consolePage))).toBeLessThan(MAXIMUM_SYNC_MS);
  expect((await status(request)).videoFormat.selected).toBe(SMALL_FORMAT.key);
});

test("the size reaching the computer follows the chosen format within 3 s", async ({ page, request }) => {
  await goLive(page, request);
  await expect.poll(async () => (await status(request)).videoFormat.available).toContain(SMALL_FORMAT.key);

  const response = await request.put(consoleUrl("/api/video-format"), { data: { format: SMALL_FORMAT.key } });
  expect(response.status()).toBe(NO_CONTENT_STATUS);

  await expect
    .poll(
      async () => {
        const video = (await status(request)).session?.video;
        return video ? `${String(video.width)}x${String(video.height)}` : "";
      },
      { timeout: SIZE_FOLLOWS_MS },
    )
    .toBe(`${String(SMALL_FORMAT.width)}x${String(SMALL_FORMAT.height)}`);
});

test("a format outside the available ones is refused", async ({ request }) => {
  const { available } = (await status(request)).videoFormat;
  const outside = TABLE_FORMATS.find((format) => !available.includes(format));
  const refused = ["1080p60", ...(outside ? [outside] : [])];

  for (const format of refused) {
    const response = await request.put(consoleUrl("/api/video-format"), { data: { format } });
    expect(response.status()).toBe(INVALID_REQUEST_STATUS);
    expect(((await response.json()) as { error: { code: string } }).error.code).toBe("invalid_request");
  }
});

async function openConsole(page: Page): Promise<Page> {
  const consolePage = await page.context().newPage();
  await consolePage.goto(consoleUrl("/"));
  await expect(consolePage.getByRole("heading", { level: 2 }).first()).toBeVisible();
  return consolePage;
}

async function recordClick(page: Page): Promise<void> {
  await page.evaluate(() => {
    document.addEventListener(
      "click",
      () => {
        document.body.dataset.clickedAt = String(Date.now());
      },
      { capture: true, once: true },
    );
  });
}

async function clickedAt(page: Page): Promise<number> {
  return Number(await page.evaluate(() => document.body.dataset.clickedAt ?? "NaN"));
}

function whenChecked(page: Page, resolution: Resolution): Promise<number> {
  const name = translate("en", resolutionKey(resolution));
  return page.evaluate(
    (optionName) =>
      new Promise<number>((resolve) => {
        const isChecked = () =>
          [...document.querySelectorAll("label")].some(
            (label) => label.dataset.checked === "true" && label.textContent?.trim() === optionName,
          );
        const observer = new MutationObserver(() => {
          if (isChecked()) {
            observer.disconnect();
            resolve(Date.now());
          }
        });
        observer.observe(document.body, { attributes: true, subtree: true, attributeFilter: ["data-checked"] });
      }),
    name,
  );
}
