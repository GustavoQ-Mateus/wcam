import { useEffect, useState } from "react";
import { appendSample, MAX_EVENTS, MAX_SAMPLES, type DevEvent, type DevMetrics } from "./dev-metrics";

export interface DevData {
  samples: DevMetrics[];
  events: DevEvent[];
}

const DEV_EVENTS_PATH = "/api/dev/events";
const METRICS_EVENT = "metrics";
const EVENT_EVENT = "event";

export function useDevEvents(): DevData {
  const [samples, setSamples] = useState<DevMetrics[]>([]);
  const [events, setEvents] = useState<DevEvent[]>([]);

  useEffect(() => {
    const source = new EventSource(DEV_EVENTS_PATH);
    source.addEventListener(METRICS_EVENT, (event) => {
      const metrics = JSON.parse(event.data as string) as DevMetrics;
      setSamples((current) => appendSample(current, metrics, MAX_SAMPLES));
    });
    source.addEventListener(EVENT_EVENT, (event) => {
      const devEvent = JSON.parse(event.data as string) as DevEvent;
      setEvents((current) => appendSample(current, devEvent, MAX_EVENTS));
    });
    return () => {
      source.close();
    };
  }, []);

  return { samples, events };
}
