import { lazy, Suspense } from "react";

const CAM_PATH_PATTERN = /^\/cam\/?$/;

const CamPage = lazy(() => import("./cam/cam-page"));
const ConsolePage = lazy(() => import("./console/console-page"));

export function Router() {
  const Page = CAM_PATH_PATTERN.test(window.location.pathname) ? CamPage : ConsolePage;
  return (
    <Suspense fallback={null}>
      <Page />
    </Suspense>
  );
}
