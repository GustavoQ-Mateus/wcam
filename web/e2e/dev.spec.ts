import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { requiredUrl } from "./environment";
import { endSession, goLive } from "./session-helpers";

const METRICS_TIMEOUT_MS = 15_000;
const CSV_HEADER_START = "at,received_fps,received_kbps";

test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
});

test("the developer console charts live numbers, pauses them and exports csv", async ({ page, request }) => {
  await goLive(page, request);
  const devPage = await page.context().newPage();
  await devPage.setViewportSize({ width: 1440, height: 900 });
  await devPage.goto(`${requiredUrl("E2E_CONSOLE_URL")}/dev`);

  await expect(devPage.getByRole("heading", { name: translate("en", "dev.title") })).toBeVisible();
  await expect(devPage.getByText(translate("en", "dev.health_ok")).first()).toBeVisible({
    timeout: METRICS_TIMEOUT_MS,
  });
  await expect(devPage.getByRole("img", { name: translate("en", "dev.chart_fps") })).toBeVisible();

  await devPage.getByRole("button", { name: translate("en", "dev.pause_charts") }).click();
  await expect(devPage.getByRole("button", { name: translate("en", "dev.resume_charts") })).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  const download = devPage.waitForEvent("download");
  await devPage.getByRole("button", { name: translate("en", "dev.export_csv") }).click();
  const csv = await readFile(await (await download).path(), "utf-8");
  const lines = csv.split("\n");
  expect(lines[0]?.startsWith(CSV_HEADER_START)).toBe(true);
  expect(lines.length).toBeGreaterThan(1);
});
