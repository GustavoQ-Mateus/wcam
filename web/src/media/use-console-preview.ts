import { previewSource } from "../data/app-preview";
import { useAppPreview } from "./use-app-preview";
import { usePreview } from "./use-preview";

const PREVIEW_BY_SOURCE = { app: useAppPreview, webrtc: usePreview };

export const useConsolePreview = PREVIEW_BY_SOURCE[previewSource(window)];
