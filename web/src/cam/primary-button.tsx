import type { ReactNode } from "react";
import styles from "./primary-button.module.scss";

interface PrimaryButtonProps {
  onClick: () => void;
  children: ReactNode;
}

export function PrimaryButton({ onClick, children }: PrimaryButtonProps) {
  return (
    <button type="button" className={styles.button} onClick={onClick}>
      {children}
    </button>
  );
}
