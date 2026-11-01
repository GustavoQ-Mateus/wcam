import { errorMessageKey } from "../data/i18n";
import { t } from "../data/language";
import { useHealth, type HealthState } from "../data/use-health";
import styles from "./console-page.module.scss";

export default function ConsolePage() {
  const health = useHealth();
  return (
    <main className={styles.page}>
      <h1 className={styles.name}>{t("app.name")}</h1>
      <p className={styles.status} data-state={health.kind} role="status">
        <span className={styles.indicator} aria-hidden="true" />
        {statusText(health)}
      </p>
    </main>
  );
}

function statusText(health: HealthState): string {
  switch (health.kind) {
    case "checking":
      return t("console.status_checking");
    case "running":
      return t("console.status_running", { version: health.version });
    case "failed":
      return t(errorMessageKey(health.code));
  }
}
