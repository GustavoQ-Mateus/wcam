import type { ReactNode } from "react";
import styles from "./console-button.module.scss";

interface ConsoleButtonProps {
  variant: "primary" | "secondary";
  onClick: () => void;
  children: ReactNode;
}

export function ConsoleButton({ variant, onClick, children }: ConsoleButtonProps) {
  return (
    <button type="button" className={styles.button} data-variant={variant} onClick={onClick}>
      {children}
    </button>
  );
}
