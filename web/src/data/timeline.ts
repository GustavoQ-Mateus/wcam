import type { LibraryVideo, TimelineClip } from "./contract";

export interface WheelZoom {
  direction: 1 | -1 | 0;
  pendingDelta: number;
}

export interface ClipPlace {
  index: number;
  offsetSeconds: number;
}

export const MIN_CLIP_SECONDS = 0.5;
export const MAX_CLIPS = 50;
export const MAX_VIDEOS = 20;
export const TRACK_HEIGHT_PIXELS = 56;
export const LIBRARY_VIDEO_TYPE = "application/x-wcam-video";

const MILLISECONDS_PER_SECOND = 1000;
const WHEEL_ZOOM_STEP_PIXELS = 50;
const WHEEL_DELTA_PIXEL = 0;
const RULER_STEPS_SECONDS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];

export function clipLength(clip: TimelineClip): number {
  return clip.outSeconds - clip.inSeconds;
}

export function timelineLength(clips: readonly TimelineClip[]): number {
  return clips.reduce((total, clip) => total + clipLength(clip), 0);
}

export function clipStarts(clips: readonly TimelineClip[]): number[] {
  const starts: number[] = [];
  let start = 0;
  for (const clip of clips) {
    starts.push(start);
    start += clipLength(clip);
  }
  return starts;
}

export function clipAtTime(clips: readonly TimelineClip[], seconds: number): ClipPlace | null {
  if (seconds < 0) {
    return null;
  }
  let start = 0;
  for (const [index, clip] of clips.entries()) {
    const end = start + clipLength(clip);
    if (seconds < end) {
      return { index, offsetSeconds: seconds - start };
    }
    start = end;
  }
  return null;
}

export function moveClip(clips: readonly TimelineClip[], from: number, to: number): TimelineClip[] {
  const target = Math.min(Math.max(0, to), clips.length - 1);
  const moved = clips[from];
  if (moved === undefined || target === from) {
    return [...clips];
  }
  const rest = clips.filter((_, index) => index !== from);
  return [...rest.slice(0, target), moved, ...rest.slice(target)];
}

export function insertVideo(
  clips: readonly TimelineClip[],
  video: LibraryVideo,
  index: number,
  id: string,
): TimelineClip[] {
  if (clips.length >= MAX_CLIPS || video.durationSeconds < MIN_CLIP_SECONDS) {
    return [...clips];
  }
  const position = Math.min(Math.max(0, index), clips.length);
  const clip = { id, videoId: video.id, inSeconds: 0, outSeconds: rounded(video.durationSeconds) };
  return [...clips.slice(0, position), clip, ...clips.slice(position)];
}

export function trimStart(clips: readonly TimelineClip[], index: number, inSeconds: number): TimelineClip[] {
  return replaceClip(clips, index, (clip) => ({
    ...clip,
    inSeconds: rounded(Math.min(Math.max(0, inSeconds), clip.outSeconds - MIN_CLIP_SECONDS)),
  }));
}

export function trimEnd(
  clips: readonly TimelineClip[],
  index: number,
  outSeconds: number,
  videoDuration: number,
): TimelineClip[] {
  return replaceClip(clips, index, (clip) => ({
    ...clip,
    outSeconds: rounded(Math.max(Math.min(videoDuration, outSeconds), clip.inSeconds + MIN_CLIP_SECONDS)),
  }));
}

export function splitAt(clips: readonly TimelineClip[], seconds: number, id: string): TimelineClip[] {
  const place = clipAtTime(clips, seconds);
  const clip = place && clips[place.index];
  if (!place || !clip || clips.length >= MAX_CLIPS) {
    return [...clips];
  }
  const cut = rounded(clip.inSeconds + place.offsetSeconds);
  if (cut - clip.inSeconds < MIN_CLIP_SECONDS || clip.outSeconds - cut < MIN_CLIP_SECONDS) {
    return [...clips];
  }
  const first = { ...clip, outSeconds: cut };
  const second = { ...clip, id, inSeconds: cut };
  return [...clips.slice(0, place.index), first, second, ...clips.slice(place.index + 1)];
}

export function deleteClip(clips: readonly TimelineClip[], index: number): TimelineClip[] {
  return clips.filter((_, position) => position !== index);
}

export function videoInUse(clips: readonly TimelineClip[], videoId: string): boolean {
  return clips.some((clip) => clip.videoId === videoId);
}

export function dropIndex(clips: readonly TimelineClip[], seconds: number): number {
  const starts = clipStarts(clips);
  const index = clips.findIndex((clip, position) => seconds < (starts[position] ?? 0) + clipLength(clip) / 2);
  return index === -1 ? clips.length : index;
}

export function reorderTarget(clips: readonly TimelineClip[], from: number, centerSeconds: number): number {
  const starts = clipStarts(clips);
  return clips.filter((clip, index) => index !== from && (starts[index] ?? 0) + clipLength(clip) / 2 < centerSeconds)
    .length;
}

export function sameClips(first: readonly TimelineClip[], second: readonly TimelineClip[]): boolean {
  return (
    first.length === second.length &&
    first.every((clip, index) => {
      const other = second[index];
      return (
        other !== undefined &&
        clip.id === other.id &&
        clip.videoId === other.videoId &&
        clip.inSeconds === other.inSeconds &&
        clip.outSeconds === other.outSeconds
      );
    })
  );
}

export function rulerStep(pixelsPerSecond: number, minimumGapPixels: number): number {
  const step = RULER_STEPS_SECONDS.find((seconds) => seconds * pixelsPerSecond >= minimumGapPixels);
  return step ?? RULER_STEPS_SECONDS[RULER_STEPS_SECONDS.length - 1] ?? 1;
}

export function filmstripFrame(video: LibraryVideo, seconds: number): number {
  if (video.durationSeconds <= 0 || video.filmstripFrames <= 0) {
    return 0;
  }
  const frame = Math.floor((seconds / video.durationSeconds) * video.filmstripFrames);
  return Math.min(Math.max(0, frame), video.filmstripFrames - 1);
}

function replaceClip(
  clips: readonly TimelineClip[],
  index: number,
  change: (clip: TimelineClip) => TimelineClip,
): TimelineClip[] {
  return clips.map((clip, position) => (position === index ? change(clip) : clip));
}

function rounded(seconds: number): number {
  return Math.round(seconds * MILLISECONDS_PER_SECOND) / MILLISECONDS_PER_SECOND;
}

export function wheelZoom(pendingDelta: number, deltaY: number, deltaMode: number): WheelZoom {
  if (deltaMode !== WHEEL_DELTA_PIXEL) {
    return { direction: deltaY < 0 ? 1 : deltaY > 0 ? -1 : 0, pendingDelta: 0 };
  }
  const total = pendingDelta + deltaY;
  if (Math.abs(total) < WHEEL_ZOOM_STEP_PIXELS) {
    return { direction: 0, pendingDelta: total };
  }
  return { direction: total < 0 ? 1 : -1, pendingDelta: 0 };
}
