import { expect, test } from "@playwright/test";
import type { Health } from "../src/data/contract";
import { translate } from "../src/data/i18n";
import { requiredUrl } from "./environment";

test("console shows the agent running", async ({ page, request }) => {
  const consoleUrl = requiredUrl("E2E_CONSOLE_URL");
  const health = (await (await request.get(`${consoleUrl}/api/health`)).json()) as Health;

  await page.goto(consoleUrl);

  await expect(page.getByRole("status")).toHaveText(
    translate("en", "console.status_running", { version: health.version }),
  );
});
