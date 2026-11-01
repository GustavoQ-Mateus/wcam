import { t } from "../data/language";
import styles from "./prompt.module.scss";

interface ConfirmationPromptProps {
  code: string;
}

const CODE_SEPARATOR = "-";

export function ConfirmationPrompt({ code }: ConfirmationPromptProps) {
  return (
    <>
      <h1 className={styles.title}>{t("cam.confirm_title")}</h1>
      <p className={styles.code}>
        <span className="visually-hidden">{code}</span>
        {code.split(CODE_SEPARATOR).map((group, index) => (
          <span key={index} aria-hidden="true">
            {group}
          </span>
        ))}
      </p>
      <p className={styles.body}>{t("cam.confirm_body")}</p>
    </>
  );
}
