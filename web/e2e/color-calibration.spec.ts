import { expect, test, type APIRequestContext } from "@playwright/test";
import type { ColorCalibration } from "../src/data/contract";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { endSession, goLive, status } from "./session-helpers";

const CALIBRATION_TIMEOUT_MS = 15_000;
const TEST_TIMEOUT_MS = 60_000;
const SETTLED_STATES: readonly ColorCalibration["state"][] = ["applied", "default"];

test.describe.configure({ mode: "serial" });
test.use({ hasTouch: true, viewport: PHONE_LANDSCAPE });

test.afterEach(async ({ request }) => {
  await endSession(request);
});

test("every connection measures the color again and settles with a delta E", async ({ page, request }) => {
  test.setTimeout(TEST_TIMEOUT_MS);
  await goLive(page, request);
  await expectSettled(request);
  await endSession(request);

  const nextPage = await page.context().newPage();
  await goLive(nextPage, request);
  await expect.poll(async () => (await calibration(request))?.state).toBe("measuring");
  await expectSettled(request);
});

async function calibration(request: APIRequestContext): Promise<ColorCalibration | undefined> {
  return (await status(request)).session?.video?.colorCalibration;
}

async function expectSettled(request: APIRequestContext): Promise<void> {
  await expect
    .poll(async () => SETTLED_STATES.includes((await calibration(request))?.state ?? "measuring"), {
      timeout: CALIBRATION_TIMEOUT_MS,
    })
    .toBe(true);
  const settled = await calibration(request);
  expect(settled?.deltaE).toEqual(expect.any(Number));
  console.log(`color calibration ${settled?.state ?? ""}, delta E ${String(settled?.deltaE)}`);
}
