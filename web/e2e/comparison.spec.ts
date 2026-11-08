import { expect, test, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { consoleUrl, endSession, goLive, status } from "./session-helpers";

const COMPARISON_TIMEOUT_MS = 10_000;
const DOWNLOAD_KEYS = [
  "console.dev_compare_download_phone",
  "console.dev_compare_download_pc",
  "console.dev_compare_download_report",
] as const;

test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
});

test("one click on the console brings both images and the data in 10 s, and all three download", async ({
  page,
  request,
}) => {
  expect((await status(request)).devTools).toBe(true);
  await goLive(page, request);
  const consolePage = await openConsoleWithSimulatedWcam(page);

  const startedAt = Date.now();
  await consolePage.getByRole("button", { name: translate("en", "console.dev_compare") }).click();

  const panel = consolePage.getByRole("region", { name: translate("en", "console.dev_compare") });
  await expect(panel.getByText(translate("en", "console.dev_compare_phone"), { exact: true })).toBeVisible({
    timeout: COMPARISON_TIMEOUT_MS,
  });
  await expect(panel.getByText(translate("en", "console.dev_compare_pc"), { exact: true })).toBeVisible();
  expect(Date.now() - startedAt).toBeLessThan(COMPARISON_TIMEOUT_MS);
  expect(await loadedImages(consolePage)).toBe(2);
  await expect(panel.getByRole("list", { name: translate("en", "console.dev_compare_grid") })).toBeVisible();

  for (const key of DOWNLOAD_KEYS) {
    const download = consolePage.waitForEvent("download");
    await panel.getByRole("link", { name: translate("en", key) }).click();
    const file = await (await download).path();
    expect(file).toBeTruthy();
  }
});

async function openConsoleWithSimulatedWcam(page: Page): Promise<Page> {
  const consolePage = await page.context().newPage();
  await consolePage.addInitScript(() => {
    const devices = navigator.mediaDevices;
    const enumerate = devices.enumerateDevices.bind(devices);
    devices.enumerateDevices = async () =>
      (await enumerate()).map((device) =>
        device.kind === "videoinput"
          ? ({
              deviceId: device.deviceId,
              groupId: device.groupId,
              kind: device.kind,
              label: "WCam",
              toJSON: () => device.toJSON(),
            } as MediaDeviceInfo)
          : device,
      );
  });
  await consolePage.goto(consoleUrl("/"));
  return consolePage;
}

function loadedImages(page: Page): Promise<number> {
  return page.evaluate(
    () =>
      [...document.querySelectorAll("figure img")].filter((image) => (image as HTMLImageElement).naturalWidth > 0)
        .length,
  );
}
