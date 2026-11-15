import type { DevEvent } from "../data/dev-metrics";
import type { MessageKey } from "../data/i18n";
import { LANGUAGE, t } from "../data/language";
import styles from "./dev.module.scss";

interface EventListProps {
  events: DevEvent[];
}

const KIND_KEYS: Readonly<Record<string, MessageKey>> = {
  session_state: "dev.event_session_state",
  controls: "dev.event_controls",
  video_format: "dev.event_video_format",
  camera_capabilities: "dev.event_camera_capabilities",
  virtual_camera: "dev.event_virtual_camera",
  episode: "dev.event_episode",
  preview: "dev.event_preview",
};
const TIME_FORMAT: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit", second: "2-digit" };

export function EventList({ events }: EventListProps) {
  return (
    <section className={styles.panel}>
      <h2 className={styles.chartTitle}>{t("dev.events")}</h2>
      {events.length === 0 ? (
        <p className={styles.empty}>{t("dev.no_data")}</p>
      ) : (
        <ol className={styles.events}>
          {[...events].reverse().map((event, index) => (
            <li key={`${event.at}-${String(index)}`} className={styles.event}>
              <time dateTime={event.at}>{new Date(event.at).toLocaleTimeString(LANGUAGE, TIME_FORMAT)}</time>
              <span className={styles.eventKind}>{kindLabel(event.kind)}</span>
              <span className={styles.eventData}>{JSON.stringify(event.data)}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function kindLabel(kind: string): string {
  const key = KIND_KEYS[kind];
  return key ? t(key) : kind;
}
