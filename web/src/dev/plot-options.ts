import uPlot from "uplot";
import type { ChartMark } from "../data/dev-view";
import type { PlotBuilder, PlotOptions, PlotTheme } from "../media/use-plot";

export type ChartTone = "primary" | "secondary" | "tertiary";

export interface LineChartExtras {
  max: number;
  marks: ChartMark[];
}

export interface HistogramExtras {
  binCount: number;
  budgetShare: number | null;
}

interface Stroke {
  color: keyof Pick<PlotTheme, "data" | "data2" | "data3">;
  width: number;
  dash: number[];
}

const STROKES: Readonly<Record<ChartTone, Stroke>> = {
  primary: { color: "data", width: 2, dash: [] },
  secondary: { color: "data2", width: 1.5, dash: [4, 3] },
  tertiary: { color: "data3", width: 1.5, dash: [1, 3] },
};
const GRID_LINES = [0.25, 0.5, 0.75];
const HAIRLINE_WIDTH = 1;
const LOSS_MARK_WIDTH = 2;
const EVENT_MARK_DASH = [2, 3];
const REFERENCE_DASH = [6, 4];
const BAR_GAP = 2;
const NO_PADDING: uPlot.Padding = [0, 0, 0, 0];

export function lineChartOptions(bandTones: ChartTone[], lineTones: ChartTone[], hasReference: boolean) {
  const build: PlotBuilder<LineChartExtras> = (theme, current) => ({
    ...bareOptions(),
    scales: {
      x: { time: false, range: (_plot, min, max) => [min, Math.max(max, min + 1)] },
      y: { range: () => [0, current().max] },
    },
    series: [
      {},
      ...[...bandTones].reverse().map((tone) => bandSeries(theme, tone)),
      ...(hasReference ? [referenceSeries(theme)] : []),
      ...lineTones.map((tone) => lineSeries(theme, tone)),
    ],
    hooks: {
      drawAxes: [
        (plot) => {
          drawGrid(plot, theme);
          drawMarks(plot, theme, current().marks);
        },
      ],
    },
  });
  return build;
}

export function sparklineOptions(): PlotBuilder<{ max: number }> {
  return (theme, current) => ({
    ...bareOptions(),
    scales: {
      x: { time: false, range: (_plot, min, max) => [min, Math.max(max, min + 1)] },
      y: { range: () => [0, current().max] },
    },
    series: [{}, lineSeries(theme, "primary")],
  });
}

export function histogramOptions(): PlotBuilder<HistogramExtras> {
  return (theme, current) => ({
    ...bareOptions(),
    scales: {
      x: { time: false, range: () => [0, current().binCount] },
      y: { range: (_plot, _min, max) => [0, Math.max(1, max)] },
    },
    series: [
      {},
      {
        stroke: "transparent",
        fill: theme.data,
        width: 0,
        points: { show: false },
        paths: barsPath(),
      },
    ],
    hooks: {
      draw: [
        (plot) => {
          const share = current().budgetShare;
          if (share !== null) {
            drawVertical(plot, share, theme.reference, HAIRLINE_WIDTH, REFERENCE_DASH, theme.pixelRatio);
          }
        },
      ],
    },
  });
}

function bareOptions(): Pick<PlotOptions, "padding" | "legend" | "cursor" | "select" | "axes"> {
  return {
    padding: NO_PADDING,
    legend: { show: false },
    cursor: { show: false },
    select: { show: false, left: 0, top: 0, width: 0, height: 0 },
    axes: [{ show: false }, { show: false }],
  };
}

function barsPath(): uPlot.Series.PathBuilder {
  const bars = uPlot.paths.bars;
  if (!bars) {
    throw new Error("uPlot was built without the bars path");
  }
  return bars({ align: 1, size: [1, Infinity], gap: BAR_GAP });
}

function lineSeries(theme: PlotTheme, tone: ChartTone): uPlot.Series {
  const stroke = STROKES[tone];
  return {
    stroke: theme[stroke.color],
    width: stroke.width,
    dash: scaled(stroke.dash, theme.pixelRatio),
    points: { show: false },
    spanGaps: false,
  };
}

function bandSeries(theme: PlotTheme, tone: ChartTone): uPlot.Series {
  return { stroke: "transparent", width: 0, fill: theme[STROKES[tone].color], fillTo: 0, points: { show: false } };
}

function referenceSeries(theme: PlotTheme): uPlot.Series {
  return {
    stroke: theme.reference,
    width: HAIRLINE_WIDTH,
    dash: scaled(REFERENCE_DASH, theme.pixelRatio),
    points: { show: false },
  };
}

function drawGrid(plot: uPlot, theme: PlotTheme): void {
  const { ctx, bbox } = plot;
  ctx.save();
  ctx.strokeStyle = theme.grid;
  ctx.lineWidth = HAIRLINE_WIDTH * theme.pixelRatio;
  ctx.beginPath();
  for (const share of GRID_LINES) {
    const y = Math.round(bbox.top + share * bbox.height) + crisp(theme.pixelRatio);
    ctx.moveTo(bbox.left, y);
    ctx.lineTo(bbox.left + bbox.width, y);
  }
  ctx.stroke();
  ctx.restore();
}

function drawMarks(plot: uPlot, theme: PlotTheme, marks: ChartMark[]): void {
  for (const mark of marks) {
    if (mark.kind === "loss") {
      drawVertical(plot, mark.share, theme.negative, LOSS_MARK_WIDTH, [], theme.pixelRatio);
    } else {
      drawVertical(plot, mark.share, theme.warning, HAIRLINE_WIDTH, EVENT_MARK_DASH, theme.pixelRatio);
    }
  }
}

function drawVertical(plot: uPlot, share: number, color: string, width: number, dash: number[], ratio: number): void {
  const { ctx, bbox } = plot;
  const x = Math.round(bbox.left + share * bbox.width);
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = width * ratio;
  ctx.setLineDash(scaled(dash, ratio));
  ctx.beginPath();
  ctx.moveTo(x, bbox.top);
  ctx.lineTo(x, bbox.top + bbox.height);
  ctx.stroke();
  ctx.restore();
}

function scaled(dash: number[], ratio: number): number[] {
  return dash.map((length) => length * ratio);
}

function crisp(ratio: number): number {
  return (HAIRLINE_WIDTH * ratio) % 2 === 1 ? 0.5 : 0;
}
