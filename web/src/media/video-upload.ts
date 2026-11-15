import { ApiError, toApiError, VIDEOS_PATH } from "../data/api-client";
import type { LibraryVideo } from "../data/contract";

export interface VideoUpload {
  done: Promise<LibraryVideo>;
  abort: () => void;
}

export type UploadRequestFactory = () => XMLHttpRequest;

const FILE_NAME_HEADER = "X-File-Name";
const CONTENT_TYPE = "application/octet-stream";
const NETWORK_ERROR_CODE = "network_error";
const ABORTED_CODE = "aborted";
const NETWORK_ERROR_STATUS = 0;
const FIRST_ERROR_STATUS = 400;

export function uploadVideo(
  file: File,
  onProgress: (fraction: number) => void,
  createRequest: UploadRequestFactory = () => new XMLHttpRequest(),
): VideoUpload {
  const request = createRequest();
  const done = new Promise<LibraryVideo>((resolve, reject) => {
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && event.total > 0) {
        onProgress(event.loaded / event.total);
      }
    });
    request.addEventListener("load", () => {
      const body = parsedBody(request.responseText);
      if (request.status >= FIRST_ERROR_STATUS) {
        reject(toApiError(body, request.status));
        return;
      }
      resolve(body as LibraryVideo);
    });
    request.addEventListener("error", () => {
      reject(new ApiError(NETWORK_ERROR_CODE, NETWORK_ERROR_STATUS, "Upload failed"));
    });
    request.addEventListener("abort", () => {
      reject(new ApiError(ABORTED_CODE, NETWORK_ERROR_STATUS, "Upload aborted"));
    });
  });
  request.open("POST", VIDEOS_PATH);
  request.setRequestHeader("Content-Type", CONTENT_TYPE);
  request.setRequestHeader(FILE_NAME_HEADER, encodeURIComponent(file.name));
  request.send(file);
  return {
    done,
    abort: () => {
      request.abort();
    },
  };
}

function parsedBody(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}
