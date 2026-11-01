import { t } from "../data/language";
import { CamMessage } from "./cam-message";
import { messageFor, type MessageState } from "./cam-messages";
import styles from "./message-layer.module.scss";

interface MessageLayerProps {
  state: MessageState;
  onStart: () => void;
}

export function MessageLayer({ state, onStart }: MessageLayerProps) {
  const key = "reason" in state ? `${state.kind}-${state.reason}` : state.kind;
  return (
    <div className={styles.layer} aria-live="polite">
      <h1 className={styles.brand}>{t("app.name")}</h1>
      <CamMessage key={key} content={messageFor(state, onStart)} />
    </div>
  );
}
