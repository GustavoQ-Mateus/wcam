import { t } from "../data/language";
import styles from "./cam-page.module.scss";

export default function CamPage() {
  return (
    <main className={styles.page}>
      <h1 className={styles.name}>{t("app.name")}</h1>
      <p className={styles.instruction}>{t("cam.pair_instruction")}</p>
    </main>
  );
}
