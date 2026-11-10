import { useEffect, useState, type ChangeEvent } from "react";
import { t } from "../data/language";
import styles from "./screenshot-button.module.scss";

interface ScreenshotButtonProps {
  onSend: (file: File) => Promise<boolean>;
}

type SendState = "idle" | "sending" | "sent" | "failed";

const PNG_TYPE = "image/png";
const RESULT_VISIBLE_MS = 3000;

export function ScreenshotButton({ onSend }: ScreenshotButtonProps) {
  const [sendState, setSendState] = useState<SendState>("idle");

  useEffect(() => {
    if (sendState !== "sent" && sendState !== "failed") {
      return;
    }
    const timer = window.setTimeout(() => {
      setSendState("idle");
    }, RESULT_VISIBLE_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [sendState]);

  const choose = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    setSendState("sending");
    onSend(file).then(
      (sent) => {
        setSendState(sent ? "sent" : "failed");
      },
      () => {
        setSendState("failed");
      },
    );
  };

  return (
    <div className={styles.dock}>
      <label className={styles.button} data-state={sendState}>
        <input
          type="file"
          className="visually-hidden"
          accept={PNG_TYPE}
          disabled={sendState === "sending"}
          onChange={choose}
        />
        {t("cam.dev_send_screenshot")}
      </label>
      <p className={styles.result} role="status" data-state={sendState}>
        {sendState === "sent" && t("cam.dev_screenshot_sent")}
        {sendState === "failed" && t("cam.dev_screenshot_failed")}
      </p>
    </div>
  );
}
