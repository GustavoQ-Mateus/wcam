import type { MessageContent } from "./cam-messages";
import styles from "./cam-message.module.scss";
import { PrimaryButton } from "./primary-button";

interface CamMessageProps {
  content: MessageContent;
}

export function CamMessage({ content }: CamMessageProps) {
  const { title, body, mark, action, reserveAction } = content;
  return (
    <section className={styles.message} aria-live="polite">
      <h1 className={styles.title} data-mark={mark}>
        {mark && <span className={styles.mark} data-mark={mark} aria-hidden="true" />}
        {title}
      </h1>
      {body && <p className={styles.body}>{body}</p>}
      {action && <PrimaryButton onClick={action.onClick}>{action.label}</PrimaryButton>}
      {!action && reserveAction && <div className={styles.actionSlot} />}
    </section>
  );
}
