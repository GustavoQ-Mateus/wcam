interface QualityIconProps {
  level: number;
}

const SEGMENT_POSITIONS = [2, 10, 18];

export function QualityIcon({ level }: QualityIconProps) {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" strokeLinejoin="round" aria-hidden="true">
      {SEGMENT_POSITIONS.map((x, index) => (
        <rect key={x} x={x} y="8.5" width="4" height="7" rx="1" fill={index < level ? "currentColor" : "none"} />
      ))}
    </svg>
  );
}
