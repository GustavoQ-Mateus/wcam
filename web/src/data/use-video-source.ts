import { useEffect, useState, useSyncExternalStore } from "react";
import { createUploadQueue, type UploadItem } from "../media/upload-queue";
import { ApiError, changeTimeline, changeVideoSource, removeVideo, seekVideo } from "./api-client";
import type { TimelineClip } from "./contract";
import { sameClips } from "./timeline";

export interface VideoSourceActions {
  uploads: readonly UploadItem[];
  errorCode: string | null;
  clips: readonly TimelineClip[];
  addFiles: (files: readonly File[]) => void;
  dismissUpload: (id: string) => void;
  use: () => void;
  backToCamera: () => void;
  remove: (videoId: string) => void;
  seek: (seconds: number) => void;
  changeClips: (clips: TimelineClip[]) => void;
}

const UNKNOWN_ERROR_CODE = "unknown";
const DRAFT_GRACE_MS = 1000;

export function useVideoSource(serverClips: readonly TimelineClip[]): VideoSourceActions {
  const [queue] = useState(() => createUploadQueue());
  const uploads = useSyncExternalStore(queue.subscribe, queue.items);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [draft, setDraft] = useState<TimelineClip[] | null>(null);

  useEffect(
    () => () => {
      queue.stop();
    },
    [queue],
  );
  if (draft && sameClips(draft, serverClips)) {
    setDraft(null);
  }

  const fail = (error: unknown) => {
    setErrorCode(error instanceof ApiError ? error.code : UNKNOWN_ERROR_CODE);
  };
  const run = (action: () => Promise<unknown>) => {
    setErrorCode(null);
    action().catch(fail);
  };

  return {
    uploads,
    errorCode,
    clips: draft ?? serverClips,
    addFiles: queue.add,
    dismissUpload: queue.dismiss,
    use: () => {
      run(() => changeVideoSource(true));
    },
    backToCamera: () => {
      run(() => changeVideoSource(false));
    },
    remove: (videoId) => {
      run(() => removeVideo(videoId));
    },
    seek: (seconds) => {
      run(() => seekVideo(seconds));
    },
    changeClips: (clips) => {
      setErrorCode(null);
      setDraft(clips);
      changeTimeline(clips)
        .catch((error: unknown) => {
          fail(error);
          setDraft(null);
        })
        .finally(() => {
          window.setTimeout(() => {
            setDraft((current) => (current === clips ? null : current));
          }, DRAFT_GRACE_MS);
        });
    },
  };
}
