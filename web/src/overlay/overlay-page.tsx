import { lazy, useEffect } from "react";
import type { OverlayRoute } from "../data/overlay";
import styles from "./overlay-page.module.scss";

const PAGES = {
  icon: lazy(() => import("./overlay-icon")),
  panel: lazy(() => import("./overlay-panel")),
  preview: lazy(() => import("./overlay-preview")),
};

interface OverlayPageProps {
  route: OverlayRoute;
}

export function OverlayPage({ route }: OverlayPageProps) {
  useEffect(() => {
    document.documentElement.classList.add(styles.overlay ?? "");
    document.documentElement.dataset.overlay = route;
  }, [route]);
  const Page = PAGES[route];
  return <Page />;
}
