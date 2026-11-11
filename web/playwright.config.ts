import { defineConfig, devices } from "@playwright/test";

const CONSOLE_ORIGIN_ARGS = process.env.E2E_CONSOLE_URL
  ? [`--unsafely-treat-insecure-origin-as-secure=${process.env.E2E_CONSOLE_URL}`]
  : [];
const FAKE_MEDIA_ARGS = [
  "--use-fake-device-for-media-stream=fps=60",
  "--use-fake-ui-for-media-stream",
  ...CONSOLE_ORIGIN_ARGS,
];
const QUALITY_SPEC = /quality\.spec\.ts/;

export default defineConfig({
  testDir: "e2e",
  forbidOnly: Boolean(process.env.CI),
  workers: 1,
  reporter: "list",
  use: {
    ignoreHTTPSErrors: true,
    locale: "en-US",
    launchOptions: { args: FAKE_MEDIA_ARGS },
  },
  projects: [
    { name: "chromium", testIgnore: QUALITY_SPEC, use: { ...devices["Desktop Chrome"], channel: "chromium" } },
    {
      name: "quality",
      testMatch: QUALITY_SPEC,
      dependencies: ["chromium"],
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          args: [...FAKE_MEDIA_ARGS, `--use-file-for-fake-video-capture=${process.env.E2E_QUALITY_REFERENCE ?? ""}`],
        },
      },
    },
  ],
});
