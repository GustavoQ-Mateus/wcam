import styles from "./rotate-phone-icon.module.scss";

export function RotatePhoneIcon() {
  return (
    <svg
      className={styles.icon}
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <g className={styles.phone}>
        <rect x="15" y="5" width="18" height="38" rx="3" />
        <path d="M21 37h6" />
      </g>
    </svg>
  );
}
