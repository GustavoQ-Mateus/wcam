import type { MessageContent } from "./cam-messages";
import styles from "./cam-message.module.scss";
import { PrimaryButton } from "./primary-button";
import { StateMark } from "./state-mark";

interface CamMessageProps {
  content: MessageContent;
}

export function CamMessage({ content }: CamMessageProps) {
  const { title, body, mark, action, reserveAction } = content;
  const Title = body ? "h2" : "p";
  return (
    <section className={styles.message}>
      <Title className={styles.title} data-mark={mark}>
        {mark && <StateMark kind={mark} />}
        {title}
      </Title>
      {body && <p className={styles.body}>{body}</p>}
      {action && <PrimaryButton onClick={action.onClick}>{action.label}</PrimaryButton>}
      {!action && reserveAction && <div className={styles.actionSlot} />}
    </section>
  );
}
