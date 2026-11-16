import type { ReactNode } from "react";
import styles from "./console-button.module.scss";

interface ConsoleButtonProps {
  variant: "primary" | "secondary";
  onClick: () => void;
  children: ReactNode;
  disabled?: boolean;
}

export function ConsoleButton({ variant, onClick, children, disabled = false }: ConsoleButtonProps) {
  return (
    <button type="button" className={styles.button} data-variant={variant} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
}
