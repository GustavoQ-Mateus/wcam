import type { ReactNode } from "react";
import styles from "./console-button.module.scss";

interface DownloadLinkProps {
  href: string;
  fileName: string;
  children: ReactNode;
}

export function DownloadLink({ href, fileName, children }: DownloadLinkProps) {
  return (
    <a className={styles.button} data-variant="secondary" href={href} download={fileName}>
      {children}
    </a>
  );
}
