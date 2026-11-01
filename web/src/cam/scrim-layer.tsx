import type { ReactNode } from "react";
import styles from "./scrim-layer.module.scss";

interface ScrimLayerProps {
  visible: boolean;
  contentKey: string;
  children: ReactNode;
}

export function ScrimLayer({ visible, contentKey, children }: ScrimLayerProps) {
  return (
    <div className={styles.scrim} data-visible={visible} aria-live="polite">
      <section key={contentKey} className={styles.content}>
        {children}
      </section>
    </div>
  );
}
