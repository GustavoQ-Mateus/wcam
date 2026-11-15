import { describe, expect, it } from "vitest";
import { chartIndexes, clampedColumn, lineChartColumns, stackedColumnsTopFirst } from "./chart-data";

describe("chart data", () => {
  it("chart columns are indexed one per sample", () => {
    expect(chartIndexes(3)).toEqual([0, 1, 2]);
  });

  it("values above the scale are drawn at the top and gaps stay gaps", () => {
    expect(clampedColumn([10, null, 45], 30)).toEqual([10, null, 30]);
  });

  it("stacked bands are cumulative with the full stack first", () => {
    const stacked = stackedColumnsTopFirst(
      [
        [1, 2],
        [3, 4],
        [5, 6],
      ],
      100,
    );

    expect(stacked).toEqual([
      [9, 12],
      [4, 6],
      [1, 2],
    ]);
  });

  it("stacked bands stop at the top of the scale", () => {
    expect(stackedColumnsTopFirst([[8], [8]], 10)).toEqual([[10], [8]]);
  });

  it("reference line repeats its value across the chart within the scale", () => {
    const columns = lineChartColumns([[1, 2, 3]], [], 30, 45);

    expect(columns.indexes).toEqual([0, 1, 2]);
    expect(columns.reference).toEqual([30, 30, 30]);
  });

  it("chart without reference has no reference column", () => {
    expect(lineChartColumns([[1]], [], 10, null).reference).toBeNull();
  });

  it("chart with only bands takes its length from the bands", () => {
    expect(lineChartColumns([], [[1, 2]], 10, null).indexes).toEqual([0, 1]);
  });
});
