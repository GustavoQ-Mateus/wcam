import { defineConfig, devices } from "@playwright/test";

const FAKE_MEDIA_ARGS = ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"];
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
    { name: "chromium", testIgnore: QUALITY_SPEC, use: { ...devices["Desktop Chrome"] } },
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
