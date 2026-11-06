import { expect, type APIRequestContext, type Page } from "@playwright/test";
import type { ColorCalibration, PairingWindow, Status } from "../src/data/contract";
import { translate } from "../src/data/i18n";
import { turnOnCamera } from "./cam-helpers";
import { requiredUrl } from "./environment";

const CREATED_STATUS = 201;
const SETTLED_CALIBRATION_STATES: readonly ColorCalibration["state"][] = ["applied", "default"];
export const NO_CONTENT_STATUS = 204;

export function consoleUrl(path: string): string {
  return `${requiredUrl("E2E_CONSOLE_URL")}${path}`;
}

export async function status(request: APIRequestContext): Promise<Status> {
  return (await (await request.get(consoleUrl("/api/status"))).json()) as Status;
}

export async function pairingFragment(request: APIRequestContext): Promise<string> {
  const response = await request.post(consoleUrl("/api/pairing"));
  expect(response.status()).toBe(CREATED_STATUS);
  return new URL(((await response.json()) as PairingWindow).url).hash;
}

export async function reachConfirmation(page: Page, request: APIRequestContext): Promise<string> {
  const fragment = await pairingFragment(request);
  await turnOnCamera(page, fragment);
  await expect(page.getByText(translate("en", "cam.confirm_title"))).toBeVisible();
  const code = (await status(request)).session?.confirmationCode ?? "";
  expect(code).not.toBe("");
  await expect(page.locator("main")).toContainText(code);
  return fragment;
}

export async function goLive(page: Page, request: APIRequestContext): Promise<void> {
  await reachConfirmation(page, request);
  expect((await request.post(consoleUrl("/api/sessions/current/confirm"))).status()).toBe(NO_CONTENT_STATUS);
  await expect(page.getByText(translate("en", "cam.live")).first()).toBeVisible();
}

export async function endSession(request: APIRequestContext): Promise<void> {
  await request.delete(consoleUrl("/api/sessions/current"));
}

export async function colorCalibration(request: APIRequestContext): Promise<ColorCalibration | undefined> {
  return (await status(request)).session?.video?.colorCalibration;
}

export async function waitForColorCalibration(request: APIRequestContext, timeout: number): Promise<void> {
  await expect
    .poll(async () => SETTLED_CALIBRATION_STATES.includes((await colorCalibration(request))?.state ?? "measuring"), {
      timeout,
    })
    .toBe(true);
}
