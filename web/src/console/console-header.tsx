import type { Badge } from "../data/console-view";
import { t } from "../data/language";
import styles from "./console-header.module.scss";
import { StatusMark } from "./status-mark";

interface ConsoleHeaderProps {
  badge: Badge | null;
}

const DEVELOPER_PATH = "/dev";

export function ConsoleHeader({ badge }: ConsoleHeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.identity}>
        <h1 className={styles.name}>{t("app.name")}</h1>
        {badge && (
          <p className={styles.badge} data-tone={badge.tone} role="status">
            <StatusMark shape={badge.shape} tone={badge.tone} />
            {t(badge.key)}
          </p>
        )}
      </div>
      <nav>
        <a className={styles.link} href={DEVELOPER_PATH}>
          {t("console.developer")}
        </a>
      </nav>
    </header>
  );
}
