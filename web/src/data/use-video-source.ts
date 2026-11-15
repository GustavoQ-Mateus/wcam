import { useEffect, useRef, useState } from "react";
import { uploadVideo, type VideoUpload } from "../media/video-upload";
import { ApiError, changeVideoSource, removeVideoFile, seekVideo } from "./api-client";

export interface VideoSourceActions {
  uploadFraction: number | null;
  errorCode: string | null;
  choose: (file: File) => void;
  use: () => void;
  backToPhone: () => void;
  remove: () => void;
  seek: (seconds: number) => void;
}

const UNKNOWN_ERROR_CODE = "unknown";
const ABORTED_CODE = "aborted";

export function useVideoSource(): VideoSourceActions {
  const [uploadFraction, setUploadFraction] = useState<number | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const uploadRef = useRef<VideoUpload | null>(null);

  useEffect(
    () => () => {
      uploadRef.current?.abort();
    },
    [],
  );

  const fail = (error: unknown) => {
    const code = error instanceof ApiError ? error.code : UNKNOWN_ERROR_CODE;
    if (code !== ABORTED_CODE) {
      setErrorCode(code);
    }
  };
  const run = (action: () => Promise<unknown>) => {
    setErrorCode(null);
    action().catch(fail);
  };

  return {
    uploadFraction,
    errorCode,
    choose: (file) => {
      uploadRef.current?.abort();
      setErrorCode(null);
      setUploadFraction(0);
      const upload = uploadVideo(file, setUploadFraction);
      uploadRef.current = upload;
      upload.done.catch(fail).finally(() => {
        if (uploadRef.current === upload) {
          uploadRef.current = null;
          setUploadFraction(null);
        }
      });
    },
    use: () => {
      run(() => changeVideoSource(true));
    },
    backToPhone: () => {
      run(() => changeVideoSource(false));
    },
    remove: () => {
      run(removeVideoFile);
    },
    seek: (seconds) => {
      run(() => seekVideo(seconds));
    },
  };
}
