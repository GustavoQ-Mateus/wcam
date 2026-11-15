export type ChartColumn = (number | null)[];

export interface LineChartColumns {
  indexes: number[];
  bands: number[][];
  reference: number[] | null;
  lines: ChartColumn[];
}

export function chartIndexes(count: number): number[] {
  return Array.from({ length: count }, (_, index) => index);
}

export function clampedColumn(values: readonly (number | null)[], max: number): ChartColumn {
  return values.map((value) => (value === null ? null : Math.min(value, max)));
}

export function stackedColumnsTopFirst(layers: readonly (readonly number[])[], max: number): number[][] {
  const count = layers[0]?.length ?? 0;
  const totals = new Array<number>(count).fill(0);
  const stacked = layers.map((layer) =>
    totals.map((total, index) => {
      totals[index] = total + (layer[index] ?? 0);
      return Math.min(totals[index], max);
    }),
  );
  return stacked.reverse();
}

export function lineChartColumns(
  lines: readonly (readonly (number | null)[])[],
  bands: readonly (readonly number[])[],
  max: number,
  reference: number | null,
): LineChartColumns {
  const count = lines[0]?.length ?? bands[0]?.length ?? 0;
  return {
    indexes: chartIndexes(count),
    bands: stackedColumnsTopFirst(bands, max),
    reference: reference === null ? null : new Array<number>(count).fill(Math.min(reference, max)),
    lines: lines.map((line) => clampedColumn(line, max)),
  };
}
