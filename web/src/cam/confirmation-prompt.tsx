import type { CodeAnswer } from "../data/cam-state";
import { t } from "../data/language";
import { PrimaryButton } from "./primary-button";
import styles from "./prompt.module.scss";
import { StateMark } from "./state-mark";

interface ConfirmationPromptProps {
  code: string;
  answer: CodeAnswer;
  onSame: () => void;
  onDifferent: () => void;
}

const CODE_SEPARATOR = "-";

export function ConfirmationPrompt({ code, answer, onSame, onDifferent }: ConfirmationPromptProps) {
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
      {answer === "none" && (
        <div className={styles.answers}>
          <PrimaryButton onClick={onSame}>{t("cam.confirm_same")}</PrimaryButton>
          <PrimaryButton quiet onClick={onDifferent}>
            {t("cam.confirm_different")}
          </PrimaryButton>
        </div>
      )}
      {answer === "same" && (
        <p className={styles.waiting}>
          <StateMark kind="waiting" />
          {t("cam.confirm_waiting_pc")}
        </p>
      )}
    </>
  );
}
