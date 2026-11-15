import type { ReactNode } from "react";
import styles from "./primary-button.module.scss";

interface PrimaryButtonProps {
  onClick: () => void;
  quiet?: boolean;
  children: ReactNode;
}

export function PrimaryButton({ onClick, quiet = false, children }: PrimaryButtonProps) {
  return (
    <button type="button" className={styles.button} data-quiet={quiet} onClick={onClick}>
      {children}
    </button>
  );
}
