import { useCallback, useEffect, useState } from "react";
import {
  DEFAULT_OVERLAY_STATE,
  parseOverlayMessage,
  type OverlayPageMessage,
  type OverlayState,
} from "../data/overlay";
import { appWebView, type WebMessageEvent } from "./app-webview";

export interface OverlayChannel {
  state: OverlayState;
  closing: boolean;
  openings: number;
  post: (message: OverlayPageMessage) => void;
}

export function useOverlayChannel(): OverlayChannel {
  const [state, setState] = useState(DEFAULT_OVERLAY_STATE);
  const [closing, setClosing] = useState(false);
  const [openings, setOpenings] = useState(0);

  useEffect(() => {
    const webview = appWebView();
    if (!webview) {
      return;
    }
    const handleMessage = (event: WebMessageEvent) => {
      const message = parseOverlayMessage(event.data);
      if (message?.type === "panel.closing") {
        setClosing(true);
        return;
      }
      if (!message) {
        return;
      }
      setState({
        edge: message.edge,
        keyboard: message.keyboard,
        hotkey: message.hotkey,
        floatingPreview: message.floatingPreview,
      });
      setClosing(false);
      setOpenings((count) => count + 1);
    };
    webview.addEventListener("message", handleMessage);
    return () => {
      webview.removeEventListener("message", handleMessage);
    };
  }, []);

  const post = useCallback((message: OverlayPageMessage) => {
    appWebView()?.postMessage(message);
  }, []);
  return { state, closing, openings, post };
}
