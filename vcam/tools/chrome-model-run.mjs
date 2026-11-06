import { createRequire } from "node:module";
import path from "node:path";

const PAGE_URL = process.env.WCAM_COLOR_VERIFY_URL ?? "http://localhost:8765/";
const RESULT_TIMEOUT_MS = 60_000;
const WEB_DIRECTORY = process.argv[2];

if (!WEB_DIRECTORY) {
  console.error("usage: node chrome-model-run.mjs <web directory with node_modules/playwright>");
  process.exit(2);
}

const require = createRequire(path.join(path.resolve(WEB_DIRECTORY), "package.json"));
const { chromium } = require("playwright");
const EXTRA_ARGS = (process.env.WCAM_CHROME_ARGS ?? "").split(" ").filter(Boolean);
const LAUNCH_ARGS = ["--use-fake-ui-for-media-stream", ...EXTRA_ARGS];

async function launch() {
  try {
    return { browser: await chromium.launch({ channel: "chrome", headless: false, args: LAUNCH_ARGS }), channel: "chrome" };
  } catch (error) {
    console.log(`channel chrome unavailable (${error.message.split("\n")[0]}); using Playwright Chromium`);
    return { browser: await chromium.launch({ headless: false, args: LAUNCH_ARGS }), channel: "playwright-chromium" };
  }
}

const { browser, channel } = await launch();
console.log(`browser: ${channel} ${browser.version()}, args: ${LAUNCH_ARGS.join(" ")}`);
try {
  const page = await browser.newPage();
  await page.goto(PAGE_URL);
  const initialText = await page.textContent("#out");
  await page.click("#go");
  await page.waitForFunction(text => document.getElementById("out").textContent !== text, initialText, {
    timeout: RESULT_TIMEOUT_MS,
  });
  console.log(await page.textContent("#out"));
} finally {
  await browser.close();
}
