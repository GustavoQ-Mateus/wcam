import { expect, test, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import type { QualityPreset } from "../src/data/quality-preset";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { consoleUrl, endSession, goLive, status } from "./session-helpers";

const MAXIMUM_SYNC_MS = 300;

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
  await request.put(consoleUrl("/api/quality-preset"), { data: { preset: "balanced" } });
});

test("a preset chosen on the phone shows on the console in under 300 ms", async ({ page, request }) => {
  await goLive(page, request);
  const consolePage = await openConsole(page);
  await page.getByRole("button", { name: translate("en", "quality.label") }).click();
  await recordClick(page);

  const checkedAt = whenChecked(consolePage, "maximum");
  await page.getByText(translate("en", "quality.maximum"), { exact: true }).click();

  expect((await checkedAt) - (await clickedAt(page))).toBeLessThan(MAXIMUM_SYNC_MS);
  expect((await status(request)).qualityPreset).toBe("maximum");
  await expect(optionLabel(page, "maximum")).toHaveAttribute("data-checked", "true");
});

test("a preset chosen on the console shows on the phone in under 300 ms", async ({ page, request }) => {
  await goLive(page, request);
  const consolePage = await openConsole(page);
  await expect(page.getByRole("button", { name: translate("en", "quality.label") })).toBeVisible();
  await recordClick(consolePage);

  const checkedAt = whenChecked(page, "light");
  await consolePage.getByText(translate("en", "quality.light"), { exact: true }).click();

  expect((await checkedAt) - (await clickedAt(consolePage))).toBeLessThan(MAXIMUM_SYNC_MS);
  expect((await status(request)).qualityPreset).toBe("light");
});

async function openConsole(page: Page): Promise<Page> {
  const consolePage = await page.context().newPage();
  await consolePage.goto(consoleUrl("/"));
  await expect(optionLabel(consolePage, "balanced")).toHaveAttribute("data-checked", "true");
  return consolePage;
}

function optionLabel(page: Page, preset: QualityPreset) {
  return page.locator("label", { hasText: translate("en", qualityNameKey(preset)) });
}

function qualityNameKey(preset: QualityPreset) {
  return `quality.${preset}` as const;
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

function whenChecked(page: Page, preset: QualityPreset): Promise<number> {
  const name = translate("en", qualityNameKey(preset));
  return page.evaluate(
    (optionName) =>
      new Promise<number>((resolve) => {
        const isChecked = () =>
          [...document.querySelectorAll("label")].some(
            (label) => label.dataset.checked === "true" && label.textContent?.startsWith(optionName),
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
