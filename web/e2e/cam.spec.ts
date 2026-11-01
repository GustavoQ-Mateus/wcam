import { expect, test } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { requiredUrl } from "./environment";

const CONSOLE_CHUNK_NAME = "console-page";

test("cam page opens over https and shows the pairing instruction", async ({ page }) => {
  const response = await page.goto(`${requiredUrl("E2E_PHONE_URL")}/cam`);

  expect(response?.url()).toMatch(/^https:/);
  await expect(page.getByText(translate("en", "cam.pair_instruction"))).toBeVisible();
});

test("cam page does not load the console chunk", async ({ page }) => {
  const requestedUrls: string[] = [];
  page.on("request", (request) => requestedUrls.push(request.url()));

  await page.goto(`${requiredUrl("E2E_PHONE_URL")}/cam`, { waitUntil: "networkidle" });
  await expect(page.getByText(translate("en", "cam.pair_instruction"))).toBeVisible();

  expect(requestedUrls.filter((url) => url.includes(CONSOLE_CHUNK_NAME))).toEqual([]);
});
