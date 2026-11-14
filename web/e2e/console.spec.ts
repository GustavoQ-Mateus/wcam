import { expect, test } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { requiredUrl } from "./environment";
import { endSession } from "./session-helpers";

test("console without a phone shows it is waiting for the phone", async ({ page, request }) => {
  await endSession(request);

  await page.goto(requiredUrl("E2E_CONSOLE_URL"));

  await expect(page.getByRole("status")).toHaveText(translate("en", "state.waiting"));
});
