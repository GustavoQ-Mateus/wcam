import { t } from "../data/language";
import styles from "./dev.module.scss";

interface DetailListProps {
  title: string;
  rows: [string, string | null][];
}

export function DetailList({ title, rows }: DetailListProps) {
  return (
    <section className={styles.panel}>
      <h2 className={styles.chartTitle}>{title}</h2>
      <dl className={styles.list}>
        {rows.map(([label, value]) => (
          <div key={label} className={styles.listRow}>
            <dt>{label}</dt>
            <dd data-empty={value === null}>{value ?? t("dev.not_reported")}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
