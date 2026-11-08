import { differenceLines } from "../data/comparison-format";
import type { ImageDifference } from "../data/contract";
import { t } from "../data/language";
import styles from "./comparison-panel.module.scss";

interface DifferenceDetailsProps {
  title: string;
  difference: ImageDifference;
}

export function DifferenceDetails({ title, difference }: DifferenceDetailsProps) {
  return (
    <section className={styles.details}>
      <h3 className={styles.detailsTitle}>{title}</h3>
      <ul className={styles.lines}>
        {differenceLines(difference).map((line) => (
          <li key={line.key}>{t(line.key, line.values)}</li>
        ))}
      </ul>
    </section>
  );
}
