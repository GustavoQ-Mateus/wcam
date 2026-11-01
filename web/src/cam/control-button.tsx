import type { ReactNode } from "react";
import styles from "./control-button.module.scss";

interface ControlButtonProps {
  label: string;
  onClick: () => void;
  children: ReactNode;
}

export function ControlButton({ label, onClick, children }: ControlButtonProps) {
  return (
    <button type="button" className={styles.button} aria-label={label} onClick={onClick}>
      {children}
    </button>
  );
}
