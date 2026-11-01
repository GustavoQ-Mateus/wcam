import styles from "./state-mark.module.scss";

export type StateMarkKind = "waiting" | "failed";

interface StateMarkProps {
  kind: StateMarkKind;
}

export function StateMark({ kind }: StateMarkProps) {
  return <span className={styles.mark} data-mark={kind} aria-hidden="true" />;
}
