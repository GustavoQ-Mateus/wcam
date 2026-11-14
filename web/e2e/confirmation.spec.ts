import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import type { CreateSessionResponse } from "../src/data/contract";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE, turnOnCamera } from "./cam-helpers";
import {
  confirmOnComputer,
  confirmOnPhone,
  endSession,
  pairingFragment,
  reachConfirmation,
  status,
} from "./session-helpers";

const LIVE_TIMEOUT_MS = 10_000;
const CONFIRMATION_TIMEOUT_TEST_MS = 180_000;
const AGENT_CONFIRMATION_TIMEOUT_MS = 130_000;
const SETTLE_MS = 2_000;
const FOREIGN_NONCE = "ffffffffffffffffffffffffffffffff";

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
});

async function expectLive(page: Page, request: APIRequestContext): Promise<void> {
  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible({ timeout: LIVE_TIMEOUT_MS });
  const { session } = await status(request);
  expect(session?.state).toBe("live");
  expect(session?.rtpPacketsBeforeLive).toBe(0);
}

async function expectNoVideoYet(page: Page, request: APIRequestContext): Promise<void> {
  await page.waitForTimeout(SETTLE_MS);
  const { session, virtualCamera } = await status(request);
  expect(session?.state).toBe("awaiting_confirmation");
  expect(session?.rtpPacketsBeforeLive).toBe(0);
  expect(virtualCamera.source).toBe("placeholder");
}

async function routeForeignComputer(page: Page): Promise<void> {
  await page.route("**/api/sessions", async (route) => {
    const response = await route.fetch();
    const body = (await response.json()) as CreateSessionResponse;
    await route.fulfill({ response, json: { ...body, confirmationNonce: FOREIGN_NONCE } });
  });
}

test("the computer confirming first waits for the phone before any video", async ({ page, request }) => {
  await reachConfirmation(page, request);

  await confirmOnComputer(request);
  await expectNoVideoYet(page, request);
  expect((await status(request)).session?.confirmations).toEqual({ pc: true, phone: false });
  await confirmOnPhone(page);

  await expectLive(page, request);
});

test("the phone confirming first waits for the computer before any video", async ({ page, request }) => {
  await reachConfirmation(page, request);

  await confirmOnPhone(page);
  await expect(page.getByText(translate("en", "cam.confirm_waiting_pc"))).toBeVisible();
  await expectNoVideoYet(page, request);
  expect((await status(request)).session?.confirmations).toEqual({ pc: false, phone: true });
  await confirmOnComputer(request);

  await expectLive(page, request);
});

test("a phone talking to another computer sees a different code and ends without sending video", async ({
  page,
  request,
}) => {
  await routeForeignComputer(page);
  await turnOnCamera(page, await pairingFragment(request));
  await expect(page.getByText(translate("en", "cam.confirm_title"))).toBeVisible();
  const consoleCode = (await status(request)).session?.confirmationCode ?? "";
  expect(consoleCode).not.toBe("");
  await expect(page.locator("main")).not.toContainText(consoleCode);

  await page.getByRole("button", { name: translate("en", "cam.confirm_different") }).click();

  await expect(page.getByText(translate("en", "cam.ended_code_different"))).toBeVisible();
  await expect.poll(async () => (await status(request)).lastEnded?.reason).toBe("rejected");
  expect((await status(request)).lastEnded?.rtpPacketsBeforeLive).toBe(0);
});

test("only the computer confirming ends at the time limit without sending video", async ({ page, request }) => {
  test.setTimeout(CONFIRMATION_TIMEOUT_TEST_MS);
  await reachConfirmation(page, request);
  await confirmOnComputer(request);
  await expectNoVideoYet(page, request);

  await expect(page.getByText(translate("en", "cam.ended_timeout"))).toBeVisible({
    timeout: AGENT_CONFIRMATION_TIMEOUT_MS,
  });

  const { lastEnded } = await status(request);
  expect(lastEnded?.reason).toBe("confirmation_timeout");
  expect(lastEnded?.rtpPacketsBeforeLive).toBe(0);
});
