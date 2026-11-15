import { ApiError } from "../data/api-client";
import { uploadVideo, type VideoUpload } from "./video-upload";

export type UploadState = "queued" | "sending" | "failed";

export interface UploadItem {
  id: string;
  name: string;
  fraction: number;
  state: UploadState;
  errorCode: string | null;
}

export interface UploadQueue {
  add: (files: readonly File[]) => void;
  dismiss: (id: string) => void;
  items: () => readonly UploadItem[];
  subscribe: (listener: () => void) => () => void;
  stop: () => void;
}

type Upload = (file: File, onProgress: (fraction: number) => void) => VideoUpload;

const UNKNOWN_ERROR_CODE = "unknown";
const ABORTED_CODE = "aborted";

export function createUploadQueue(
  upload: Upload = uploadVideo,
  createId: () => string = () => crypto.randomUUID(),
): UploadQueue {
  let items: readonly UploadItem[] = [];
  const files = new Map<string, File>();
  const listeners = new Set<() => void>();
  let current: VideoUpload | null = null;

  const publish = (next: readonly UploadItem[]) => {
    items = next;
    for (const listener of listeners) {
      listener();
    }
  };
  const update = (id: string, change: Partial<UploadItem>) => {
    publish(items.map((item) => (item.id === id ? { ...item, ...change } : item)));
  };
  const remove = (id: string) => {
    files.delete(id);
    publish(items.filter((item) => item.id !== id));
  };
  const fail = (id: string, error: unknown) => {
    const code = error instanceof ApiError ? error.code : UNKNOWN_ERROR_CODE;
    files.delete(id);
    if (code === ABORTED_CODE) {
      remove(id);
      return;
    }
    update(id, { state: "failed", errorCode: code });
  };
  const sendNext = () => {
    const next = items.find((item) => item.state === "queued");
    const file = next && files.get(next.id);
    if (current || !next || !file) {
      return;
    }
    update(next.id, { state: "sending" });
    const sending = upload(file, (fraction) => {
      update(next.id, { fraction });
    });
    current = sending;
    sending.done
      .then(
        () => {
          remove(next.id);
        },
        (error: unknown) => {
          fail(next.id, error);
        },
      )
      .finally(() => {
        if (current === sending) {
          current = null;
          sendNext();
        }
      });
  };

  return {
    add: (added) => {
      const queued = added.map((file) => {
        const id = createId();
        files.set(id, file);
        return { id, name: file.name, fraction: 0, state: "queued" as const, errorCode: null };
      });
      publish([...items, ...queued]);
      sendNext();
    },
    dismiss: (id) => {
      if (items.some((item) => item.id === id && item.state === "failed")) {
        remove(id);
      }
    },
    items: () => items,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    stop: () => {
      const sending = current;
      current = null;
      files.clear();
      publish([]);
      sending?.abort();
    },
  };
}
