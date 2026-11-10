const CONTINUOUS = "continuous";
const MODE_NAMES = ["exposureMode", "whiteBalanceMode", "focusMode"] as const;

type ModeName = (typeof MODE_NAMES)[number];

export function continuousModes(track: MediaStreamTrack): MediaTrackConstraintSet[] {
  const capabilities = track.getCapabilities() as Partial<Record<ModeName, unknown>>;
  const modes = MODE_NAMES.filter((name) => {
    const offered = capabilities[name];
    return Array.isArray(offered) && offered.includes(CONTINUOUS);
  });
  if (modes.length === 0) {
    return [];
  }
  return [Object.fromEntries(modes.map((name) => [name, CONTINUOUS])) as MediaTrackConstraintSet];
}

export async function requestContinuousModes(track: MediaStreamTrack): Promise<void> {
  const advanced = continuousModes(track);
  if (advanced.length > 0) {
    await track.applyConstraints({ ...track.getConstraints(), advanced }).catch(() => undefined);
  }
}
