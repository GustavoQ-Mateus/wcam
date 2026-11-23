import { describe, expect, it } from "vitest";
import type { LibraryVideo, TimelineClip } from "./contract";
import {
  clipAtTime,
  clipStarts,
  deleteClip,
  dropIndex,
  filmstripFrame,
  insertVideo,
  MAX_CLIPS,
  moveClip,
  reorderTarget,
  rulerStep,
  sameClips,
  splitAt,
  timelineLength,
  trimEnd,
  trimStart,
  videoInUse,
  wheelZoom,
} from "./timeline";

const VIDEO: LibraryVideo = {
  id: "v1",
  name: "beach.mov",
  durationSeconds: 12,
  width: 1920,
  height: 1080,
  fps: 30,
  codec: "hevc",
  filmstripFrames: 60,
};
const CLIPS: TimelineClip[] = [
  { id: "a", videoId: "v1", inSeconds: 0, outSeconds: 4 },
  { id: "b", videoId: "v2", inSeconds: 1, outSeconds: 3 },
  { id: "c", videoId: "v1", inSeconds: 6, outSeconds: 12 },
];

function ids(clips: TimelineClip[]): string[] {
  return clips.map((clip) => clip.id);
}

describe("timeline", () => {
  it("timeline length is the sum of the clip lengths", () => {
    expect(timelineLength(CLIPS)).toBe(12);
  });

  it("clip starts follow each other without gaps", () => {
    expect(clipStarts(CLIPS)).toEqual([0, 4, 6]);
  });

  it("time inside the second clip maps to that clip and its offset", () => {
    expect(clipAtTime(CLIPS, 5)).toEqual({ index: 1, offsetSeconds: 1 });
  });

  it("time at the end of the timeline maps to no clip", () => {
    expect(clipAtTime(CLIPS, 12)).toBeNull();
  });

  it("moving a clip forward places it at the target index", () => {
    expect(ids(moveClip(CLIPS, 0, 2))).toEqual(["b", "c", "a"]);
  });

  it("moving a clip past the end keeps it last", () => {
    expect(ids(moveClip(CLIPS, 1, 9))).toEqual(["a", "c", "b"]);
  });

  it("inserting a video adds the whole video at the index", () => {
    const clips = insertVideo(CLIPS, VIDEO, 1, "new");

    expect(ids(clips)).toEqual(["a", "new", "b", "c"]);
    expect(clips[1]).toEqual({ id: "new", videoId: "v1", inSeconds: 0, outSeconds: 12 });
  });

  it("inserting into a full timeline changes nothing", () => {
    const full = Array.from({ length: MAX_CLIPS }, (_, index) => ({ ...CLIPS[0], id: String(index) }) as TimelineClip);

    expect(insertVideo(full, VIDEO, 0, "new")).toHaveLength(MAX_CLIPS);
  });

  it("trimming the start keeps at least half a second in the clip", () => {
    expect(trimStart(CLIPS, 0, 3.9)[0]?.inSeconds).toBe(3.5);
  });

  it("trimming the start never goes before the video start", () => {
    expect(trimStart(CLIPS, 1, -2)[1]?.inSeconds).toBe(0);
  });

  it("trimming the end never goes past the video duration", () => {
    expect(trimEnd(CLIPS, 0, 20, VIDEO.durationSeconds)[0]?.outSeconds).toBe(12);
  });

  it("trimming the end keeps at least half a second in the clip", () => {
    expect(trimEnd(CLIPS, 2, 6.1, VIDEO.durationSeconds)[2]?.outSeconds).toBe(6.5);
  });

  it("trim values are rounded to milliseconds", () => {
    expect(trimStart(CLIPS, 2, 7.123456)[2]?.inSeconds).toBe(7.123);
  });

  it("splitting at the playhead cuts the clip under it in two", () => {
    const clips = splitAt(CLIPS, 8, "half");

    expect(clips.slice(2)).toEqual([
      { id: "c", videoId: "v1", inSeconds: 6, outSeconds: 8 },
      { id: "half", videoId: "v1", inSeconds: 8, outSeconds: 12 },
    ]);
  });

  it("splitting closer than half a second to a clip edge changes nothing", () => {
    expect(splitAt(CLIPS, 4.2, "half")).toEqual(CLIPS);
  });

  it("deleting a clip removes only that clip", () => {
    expect(ids(deleteClip(CLIPS, 1))).toEqual(["a", "c"]);
  });

  it("a video is in use while any clip points to it", () => {
    expect(videoInUse(CLIPS, "v2")).toBe(true);
    expect(videoInUse(CLIPS, "v3")).toBe(false);
  });

  it("dropping before the middle of a clip inserts before it", () => {
    expect(dropIndex(CLIPS, 4.5)).toBe(1);
    expect(dropIndex(CLIPS, 5.5)).toBe(2);
    expect(dropIndex(CLIPS, 11)).toBe(3);
  });

  it("dragged clip lands after every clip whose middle it passed", () => {
    expect(reorderTarget(CLIPS, 0, 6)).toBe(1);
    expect(reorderTarget(CLIPS, 0, 10)).toBe(2);
    expect(reorderTarget(CLIPS, 2, 1)).toBe(0);
  });

  it("clips with the same values are the same timeline", () => {
    expect(
      sameClips(
        CLIPS,
        CLIPS.map((clip) => ({ ...clip })),
      ),
    ).toBe(true);
    expect(sameClips(CLIPS, trimStart(CLIPS, 0, 1))).toBe(false);
  });

  it("ruler step is the smallest that keeps labels apart", () => {
    expect(rulerStep(100, 64)).toBe(1);
    expect(rulerStep(10, 64)).toBe(10);
    expect(rulerStep(1, 64)).toBe(120);
  });

  it("filmstrip frame follows the time in the video", () => {
    expect(filmstripFrame(VIDEO, 6)).toBe(30);
    expect(filmstripFrame(VIDEO, 12)).toBe(59);
  });

  it("one mouse wheel notch with ctrl zooms one level, up to zoom in and down to zoom out", () => {
    expect([wheelZoom(0, -100, 0), wheelZoom(0, 100, 0), wheelZoom(0, -3, 1)]).toEqual([
      { direction: 1, pendingDelta: 0 },
      { direction: -1, pendingDelta: 0 },
      { direction: 1, pendingDelta: 0 },
    ]);
  });

  it("small trackpad pinch deltas add up before zooming one level", () => {
    const first = wheelZoom(0, -20, 0);
    const second = wheelZoom(first.pendingDelta, -20, 0);
    const third = wheelZoom(second.pendingDelta, -20, 0);

    expect([first, second, third]).toEqual([
      { direction: 0, pendingDelta: -20 },
      { direction: 0, pendingDelta: -40 },
      { direction: 1, pendingDelta: 0 },
    ]);
  });
});
