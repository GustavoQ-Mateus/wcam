import { expect, test, type APIRequestContext } from "@playwright/test";
import { PHONE_LANDSCAPE } from "./cam-helpers";
import { colorCalibration, endSession, goLive, waitForColorCalibration } from "./session-helpers";

const CALIBRATION_TIMEOUT_MS = 15_000;
const TEST_TIMEOUT_MS = 60_000;
const MAXIMUM_DELTA_E = 2;

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
  await expect.poll(async () => (await colorCalibration(request))?.state).toBe("measuring");
  await expectSettled(request);
});

async function expectSettled(request: APIRequestContext): Promise<void> {
  await waitForColorCalibration(request, CALIBRATION_TIMEOUT_MS);
  const settled = await colorCalibration(request);
  expect(settled?.deltaE ?? Infinity).toBeLessThan(MAXIMUM_DELTA_E);
  console.log(`color calibration ${settled?.state ?? ""}, delta E ${String(settled?.deltaE)}`);
}
