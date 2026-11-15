type Report = Readonly<Record<string, unknown>>;

const STATS_TYPE = "stats";
const OUTBOUND_FIELDS = [
  "framesPerSecond",
  "framesSent",
  "framesEncoded",
  "keyFramesEncoded",
  "bytesSent",
  "qualityLimitationReason",
  "nackCount",
  "pliCount",
  "frameWidth",
  "frameHeight",
] as const;
const REMOTE_INBOUND_FIELDS = ["roundTripTime", "jitter", "packetsLost"] as const;

export function statsMessage(reports: Iterable<Report>, at: number): string {
  const all = [...reports];
  return JSON.stringify({
    type: STATS_TYPE,
    at,
    outbound: pick(videoReport(all, "outbound-rtp"), OUTBOUND_FIELDS),
    remoteInbound: pick(videoReport(all, "remote-inbound-rtp"), REMOTE_INBOUND_FIELDS),
  });
}

function videoReport(reports: readonly Report[], type: string): Report | undefined {
  return reports.find((report) => report.type === type && report.kind === "video");
}

function pick(report: Report | undefined, fields: readonly string[]): Record<string, unknown> | null {
  if (!report) {
    return null;
  }
  return Object.fromEntries(fields.map((field) => [field, reportValue(report[field])]));
}

function reportValue(value: unknown): number | string | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return typeof value === "string" ? value : null;
}
