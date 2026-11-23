import { useCallback, useEffect, useRef, useState } from "react";
import { appPreviewState, isNewerFrame, nv12Size, parseAppPreviewMessage, type PreviewSlot } from "../data/app-preview";
import type { PreviewState } from "../data/preview-state";
import { appWebView, type SharedBufferEvent, type WebMessageEvent } from "./app-webview";
import { createNv12Renderer, type Nv12Renderer } from "./nv12-renderer";
import { useDocumentVisible } from "./use-document-visible";
import type { Preview } from "./use-preview";

interface FrameBuffer {
  buffer: ArrayBuffer;
  width: number;
  height: number;
}

export function useAppPreview(enabled: boolean): Preview {
  const active = useDocumentVisible() && enabled;
  const [state, setState] = useState<PreviewState>("connecting");
  const [attempt, setAttempt] = useState(0);
  const [startedFor, setStartedFor] = useState(active);
  const rendererRef = useRef<Nv12Renderer | null>(null);

  if (startedFor !== active) {
    setStartedFor(active);
    setState(appPreviewState("start"));
  }

  useEffect(() => {
    const webview = appWebView();
    if (!active || !webview) {
      return;
    }
    const buffers = new Map<PreviewSlot, FrameBuffer>();
    let lastSequence: number | null = null;
    const keepBuffer = (event: SharedBufferEvent) => {
      const message = parseAppPreviewMessage(event.additionalData);
      const buffer = event.getBuffer();
      if (message?.type !== "preview.buffer" || buffer.byteLength < nv12Size(message.width, message.height)) {
        webview.releaseBuffer(buffer);
        return;
      }
      const previous = buffers.get(message.slot);
      if (previous) {
        webview.releaseBuffer(previous.buffer);
      }
      buffers.set(message.slot, { buffer, width: message.width, height: message.height });
      lastSequence = null;
    };
    const showFrame = (slot: PreviewSlot, sequence: number) => {
      const frame = buffers.get(slot);
      if (!frame || !isNewerFrame(lastSequence, sequence)) {
        return;
      }
      lastSequence = sequence;
      rendererRef.current?.draw(frame.buffer, frame.width, frame.height);
      setState(appPreviewState("frame"));
    };
    const handleMessage = (event: WebMessageEvent) => {
      const message = parseAppPreviewMessage(event.data);
      if (message?.type === "preview.idle") {
        setState(appPreviewState("idle"));
        return;
      }
      if (message?.type !== "preview.frame") {
        return;
      }
      showFrame(message.slot, message.sequence);
      webview.postMessage({ type: "preview.release", slot: message.slot });
    };
    webview.addEventListener("sharedbufferreceived", keepBuffer);
    webview.addEventListener("message", handleMessage);
    webview.postMessage({ type: "preview.start" });
    return () => {
      webview.removeEventListener("sharedbufferreceived", keepBuffer);
      webview.removeEventListener("message", handleMessage);
      webview.postMessage({ type: "preview.stop" });
      buffers.forEach((frame) => {
        webview.releaseBuffer(frame.buffer);
      });
    };
  }, [active, attempt]);

  const attach = useCallback((canvas: HTMLCanvasElement | null) => {
    rendererRef.current?.dispose();
    rendererRef.current = canvas ? createNv12Renderer(canvas) : null;
  }, []);
  const showAgain = useCallback(() => {
    setState(appPreviewState("start"));
    setAttempt((count) => count + 1);
  }, []);
  return { surface: { kind: "canvas", attach }, state, showAgain };
}
