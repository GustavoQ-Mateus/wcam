import type { Page } from "@playwright/test";
import { translate } from "../src/data/i18n";
import { requiredUrl } from "./environment";

export const PHONE_LANDSCAPE = { width: 844, height: 390 };
export const PHONE_PORTRAIT = { width: 390, height: 844 };

export interface TrackSettings {
  readyState: string;
  width: number;
  height: number;
  fps: number;
}

export function camUrl(fragment = ""): string {
  return `${requiredUrl("E2E_PHONE_URL")}/cam${fragment}`;
}

export async function turnOnCamera(page: Page, fragment: string): Promise<void> {
  await page.goto(camUrl(fragment));
  await page.getByRole("button", { name: translate("en", "cam.intro_action") }).click();
}

export async function trackSettings(page: Page): Promise<TrackSettings> {
  return page.evaluate(() => {
    const stream = document.querySelector("video")?.srcObject;
    const track = stream instanceof MediaStream ? stream.getVideoTracks()[0] : undefined;
    const settings = track?.getSettings() ?? {};
    return {
      readyState: track?.readyState ?? "missing",
      width: settings.width ?? 0,
      height: settings.height ?? 0,
      fps: Math.round(settings.frameRate ?? 0),
    };
  });
}
