import { lazy, Suspense } from "react";
import { overlayRoute } from "./data/overlay";
import { OverlayPage } from "./overlay/overlay-page";

const CAM_PATH_PATTERN = /^\/cam\/?$/;
const DEV_PATH_PATTERN = /^\/dev\/?$/;

const CamPage = lazy(() => import("./cam/cam-page"));
const ConsolePage = lazy(() => import("./console/console-page"));
const DevPage = lazy(() => import("./dev/dev-page"));

const OVERLAY_ROUTE = overlayRoute(window.location.pathname);
const Page = pageFor(window.location.pathname);

export function Router() {
  return <Suspense fallback={null}>{OVERLAY_ROUTE ? <OverlayPage route={OVERLAY_ROUTE} /> : <Page />}</Suspense>;
}

function pageFor(path: string) {
  if (CAM_PATH_PATTERN.test(path)) {
    return CamPage;
  }
  return DEV_PATH_PATTERN.test(path) ? DevPage : ConsolePage;
}
