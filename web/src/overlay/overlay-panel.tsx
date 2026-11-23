import { useCallback, useEffect, useRef, type KeyboardEvent } from "react";
import { changeVideoSource } from "../data/api-client";
import { stateBadge } from "../data/console-view";
import { t } from "../data/language";
import { panelSummary, quickActions, type QuickAction } from "../data/overlay";
import { useConsole } from "../data/use-console";
import { StatusMark } from "../console/status-mark";
import { useOverlayChannel } from "../media/use-overlay-channel";
import { useReportedSize } from "../media/use-reported-size";
import styles from "./overlay-panel.module.scss";

const SUMMARY_SEPARATOR = " · ";
const NEXT_KEYS: ReadonlySet<string> = new Set(["ArrowDown", "ArrowRight"]);
const PREVIOUS_KEYS: ReadonlySet<string> = new Set(["ArrowUp", "ArrowLeft"]);

export default function OverlayPanel() {
  const { status, changeControls } = useConsole();
  const { state, closing, openings, post } = useOverlayChannel();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const reportSize = useReportedSize(
    useCallback(
      (width: number, height: number) => {
        post({ type: "window.size", width, height });
      },
      [post],
    ),
  );

  useEffect(() => {
    if (state.keyboard) {
      panelRef.current?.querySelector<HTMLButtonElement>("button:enabled")?.focus();
    }
  }, [state.keyboard, openings]);

  const finish = () => {
    if (state.keyboard) {
      post({ type: "panel.close" });
    }
  };
  const run = (action: QuickAction) => {
    if (action.kind === "controls") {
      changeControls(action.patch);
    } else {
      void changeVideoSource(action.active).catch(() => undefined);
    }
    finish();
  };
  const ask = (message: Parameters<typeof post>[0]) => {
    post(message);
    finish();
  };
  const badge = status ? stateBadge(status) : null;

  return (
    <div
      key={openings}
      ref={(element) => {
        panelRef.current = element;
        return reportSize(element);
      }}
      className={styles.panel}
      data-edge={state.edge}
      data-closing={closing}
      role="menu"
      aria-label={t("overlay.panel")}
      onKeyDown={(event) => {
        handleKeys(event, () => {
          post({ type: "panel.close" });
        });
      }}
    >
      <p className={styles.summary}>
        {badge && <StatusMark shape={badge.shape} tone={badge.tone} />}
        {status
          ? panelSummary(status)
              .map((key) => t(key))
              .join(SUMMARY_SEPARATOR)
          : t("state.waiting")}
      </p>
      <div className={styles.group}>
        {status &&
          quickActions(status).map((action) => (
            <button
              key={action.kind === "controls" ? Object.keys(action.patch).join() : action.kind}
              type="button"
              role="menuitem"
              className={styles.item}
              disabled={!action.enabled}
              aria-pressed={action.kind === "controls" ? action.pressed : undefined}
              onClick={() => {
                run(action);
              }}
            >
              {t(action.labelKey)}
            </button>
          ))}
      </div>
      <div className={styles.group}>
        <button
          type="button"
          role="menuitem"
          className={styles.item}
          onClick={() => {
            ask({ type: "floatingPreview.toggle" });
          }}
        >
          {t(state.floatingPreview ? "overlay.preview_off" : "overlay.preview_on")}
        </button>
        <button
          type="button"
          role="menuitem"
          className={styles.item}
          onClick={() => {
            ask({ type: "console.open" });
          }}
        >
          {t("tray.open_console")}
        </button>
        <button
          type="button"
          role="menuitem"
          className={styles.item}
          onClick={() => {
            ask({ type: "overlay.hide" });
          }}
        >
          {t("overlay.hide")}
        </button>
      </div>
      <footer className={styles.help}>
        <p>{t("overlay.drag_hint")}</p>
        {state.hotkey && <p>{t("overlay.hotkey", { keys: state.hotkey })}</p>}
      </footer>
    </div>
  );
}

function handleKeys(event: KeyboardEvent<HTMLDivElement>, close: () => void) {
  if (event.key === "Escape") {
    close();
    return;
  }
  const step = focusStep(event.key);
  if (step === 0) {
    return;
  }
  event.preventDefault();
  const items = [...event.currentTarget.querySelectorAll<HTMLButtonElement>("button:enabled")];
  const current = items.indexOf(document.activeElement as HTMLButtonElement);
  items.at((current + step) % items.length)?.focus();
}

function focusStep(key: string): number {
  if (NEXT_KEYS.has(key)) {
    return 1;
  }
  return PREVIOUS_KEYS.has(key) ? -1 : 0;
}
