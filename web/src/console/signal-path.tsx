import type { BadgeShape, BadgeTone, PathState, PathStep } from "../data/console-view";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import styles from "./side-panel.module.scss";
import { StatusMark } from "./status-mark";

interface SignalPathProps {
  steps: PathStep[];
  problemKey: MessageKey | null;
}

const MARKS: Readonly<Record<PathState, { shape: BadgeShape; tone: BadgeTone }>> = {
  ok: { shape: "dot", tone: "live" },
  waiting: { shape: "ring", tone: "neutral" },
  problem: { shape: "triangle", tone: "negative" },
};

export function SignalPath({ steps, problemKey }: SignalPathProps) {
  return (
    <section className={styles.panel}>
      <h2 className={styles.title}>{t("console.path_title")}</h2>
      <ul className={styles.rows}>
        {steps.map((step) => (
          <li key={step.nameKey} className={styles.row} data-state={step.state}>
            <StatusMark {...MARKS[step.state]} />
            <span className={styles.rowName}>{t(step.nameKey)}</span>
            <span className={styles.rowNote}>
              {t(step.noteKey, step.count === undefined ? undefined : { count: String(step.count) })}
            </span>
          </li>
        ))}
      </ul>
      {problemKey && <p className={styles.problem}>{t(problemKey)}</p>}
    </section>
  );
}
