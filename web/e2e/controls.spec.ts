import { expect, test, type Locator, type Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { requiredUrl } from "./environment";
import { endSession, goLive, status } from "./session-helpers";

const CHANGE_BUDGET_MS = 300;
const APPEAR_TIMEOUT_MS = 5_000;

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
  await request.patch(`${requiredUrl("E2E_CONSOLE_URL")}/api/controls`, { data: { mirror: false } });
});

async function openConsole(page: Page): Promise<Page> {
  const consolePage = await page.context().newPage();
  await consolePage.setViewportSize({ width: 1440, height: 900 });
  await consolePage.goto(requiredUrl("E2E_CONSOLE_URL"));
  await expect(consolePage.getByRole("status")).toHaveText(translate("en", "state.live"));
  return consolePage;
}

async function watchFor(page: Page, selector: string, text: string): Promise<() => Promise<number>> {
  await page.evaluate(
    ([css, expected]) => {
      const found = () =>
        [...document.querySelectorAll(css)].some((element) => element.textContent.trim() === expected);
      const target = window as unknown as { seenAt: Promise<number> };
      target.seenAt = new Promise((resolve) => {
        const observer = new MutationObserver(() => {
          if (found()) {
            observer.disconnect();
            resolve(Date.now());
          }
        });
        observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true });
      });
    },
    [selector, text] as const,
  );
  return () => page.evaluate(() => (window as unknown as { seenAt: Promise<number> }).seenAt);
}

async function watchPressed(page: Page, name: string): Promise<() => Promise<number>> {
  await page.evaluate((label) => {
    const pressed = () =>
      [...document.querySelectorAll("button[aria-pressed='true']")].some(
        (button) => button.textContent.trim() === label || button.getAttribute("aria-label") === label,
      );
    const target = window as unknown as { seenAt: Promise<number> };
    target.seenAt = new Promise((resolve) => {
      const observer = new MutationObserver(() => {
        if (pressed()) {
          observer.disconnect();
          resolve(Date.now());
        }
      });
      observer.observe(document.body, { subtree: true, attributes: true, childList: true });
    });
  }, name);
  return () => page.evaluate(() => (window as unknown as { seenAt: Promise<number> }).seenAt);
}

async function timedClick(page: Page, button: Locator): Promise<number> {
  await page.evaluate(() => {
    document.addEventListener(
      "click",
      () => {
        (window as unknown as { clickedAt: number }).clickedAt = Date.now();
      },
      { capture: true, once: true },
    );
  });
  await button.click();
  return page.evaluate(() => (window as unknown as { clickedAt: number }).clickedAt);
}

test("freezing on the computer shows on the phone in under 300 ms", async ({ page, request }) => {
  await goLive(page, request);
  const consolePage = await openConsole(page);
  const seen = await watchFor(page, "p", translate("en", "cam.frozen"));

  const startedAt = await timedClick(
    consolePage,
    consolePage.getByRole("button", { name: translate("en", "controls.freeze") }),
  );

  expect((await seen()) - startedAt).toBeLessThan(CHANGE_BUDGET_MS);
  await expect(page.getByText(translate("en", "cam.frozen"))).toBeVisible();
  await expect
    .poll(async () => (await status(request)).virtualCamera.source, { timeout: APPEAR_TIMEOUT_MS })
    .toBe("held");
});

test("turning the camera off on the phone shows on the computer in under 300 ms", async ({ page, request }) => {
  await goLive(page, request);
  const consolePage = await openConsole(page);
  const seen = await watchFor(consolePage, "[role='status']", translate("en", "state.camera_off"));

  const startedAt = await timedClick(page, page.getByRole("button", { name: translate("en", "controls.camera_off") }));

  expect((await seen()) - startedAt).toBeLessThan(CHANGE_BUDGET_MS);
  await expect(page.getByText(translate("en", "cam.camera_off"))).toBeVisible();
  await expect
    .poll(async () => (await status(request)).virtualCamera.source, { timeout: APPEAR_TIMEOUT_MS })
    .toBe("camera_off");
});

test("turning the camera back on from the computer brings the phone back live", async ({ page, request }) => {
  await goLive(page, request);
  const consolePage = await openConsole(page);
  await page.getByRole("button", { name: translate("en", "controls.camera_off") }).click();
  await expect(consolePage.getByRole("status")).toHaveText(translate("en", "state.camera_off"));

  await consolePage
    .getByRole("button", { name: translate("en", "controls.camera_on") })
    .first()
    .click();

  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible({ timeout: APPEAR_TIMEOUT_MS });
  await expect
    .poll(async () => (await status(request)).virtualCamera.source, { timeout: APPEAR_TIMEOUT_MS })
    .toBe("phone");
});

test("mirroring on the phone shows on the computer in under 300 ms", async ({ page, request }) => {
  await goLive(page, request);
  const consolePage = await openConsole(page);
  const seen = await watchPressed(consolePage, translate("en", "controls.mirror"));
  await page.getByRole("button", { name: translate("en", "format.label"), exact: true }).click();

  const startedAt = await timedClick(page, page.getByRole("switch", { name: translate("en", "cam.mirror_apps") }));

  expect((await seen()) - startedAt).toBeLessThan(CHANGE_BUDGET_MS);
  expect((await status(request)).controls.mirror).toBe(true);
});
