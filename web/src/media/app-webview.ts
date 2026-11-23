import type { PageMessage } from "../data/app-preview";

export interface SharedBufferEvent extends Event {
  additionalData: unknown;
  getBuffer: () => ArrayBuffer;
}

export interface WebMessageEvent extends Event {
  data: unknown;
}

interface AppWebViewEvents {
  message: WebMessageEvent;
  sharedbufferreceived: SharedBufferEvent;
}

export interface AppWebView {
  postMessage: (message: PageMessage) => void;
  releaseBuffer: (buffer: ArrayBuffer) => void;
  addEventListener: <Name extends keyof AppWebViewEvents>(
    name: Name,
    listener: (event: AppWebViewEvents[Name]) => void,
  ) => void;
  removeEventListener: <Name extends keyof AppWebViewEvents>(
    name: Name,
    listener: (event: AppWebViewEvents[Name]) => void,
  ) => void;
}

declare global {
  interface Window {
    chrome?: { webview?: AppWebView };
  }
}

export function appWebView(): AppWebView | null {
  return window.chrome?.webview ?? null;
}
