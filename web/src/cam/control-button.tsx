import type { ReactNode } from "react";
import styles from "./control-button.module.scss";

interface ControlButtonProps {
  label: string;
  describedBy?: string;
  expanded?: boolean;
  pressed?: boolean;
  controls?: string;
  onClick: () => void;
  children: ReactNode;
}

export function ControlButton({
  label,
  describedBy,
  expanded,
  pressed,
  controls,
  onClick,
  children,
}: ControlButtonProps) {
  return (
    <button
      type="button"
      className={styles.button}
      aria-label={label}
      aria-describedby={describedBy}
      aria-expanded={expanded}
      aria-pressed={pressed}
      aria-controls={controls}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
