const UNKNOWN_ERROR_NAME = "UnknownError";

export function constraintFailure(requested: string, error: unknown): string {
  return `WCam could not apply ${requested} to the camera: ${errorName(error)}`;
}

function errorName(error: unknown): string {
  if (typeof error === "object" && error !== null && "name" in error && typeof error.name === "string") {
    return error.name;
  }
  return UNKNOWN_ERROR_NAME;
}
