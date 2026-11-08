import type { CSSProperties } from "react";
import { gridCells } from "../data/comparison-format";
import type { ImageDifference } from "../data/contract";
import { t } from "../data/language";
import styles from "./comparison-image.module.scss";

interface ComparisonImageProps {
  label: string;
  time: string;
  src: string;
  width: number;
  height: number;
  grid?: ImageDifference["grid"] | undefined;
}

export function ComparisonImage({ label, time, src, width, height, grid }: ComparisonImageProps) {
  const frameStyle = { "--frame-ratio": `${String(width)} / ${String(height)}` } as CSSProperties;
  return (
    <figure className={styles.figure}>
      <div className={styles.frame} style={frameStyle}>
        <img className={styles.image} src={src} alt="" />
        {grid && <DifferenceGrid grid={grid} />}
      </div>
      <figcaption className={styles.caption}>
        <span className={styles.label}>{label}</span>
        <span className={styles.time}>{time}</span>
        {grid && <span className={styles.gridLabel}>{t("console.dev_compare_grid")}</span>}
      </figcaption>
    </figure>
  );
}

function DifferenceGrid({ grid }: { grid: ImageDifference["grid"] }) {
  const gridStyle = {
    "--grid-columns": String(grid.columns),
    "--grid-rows": String(grid.rows),
  } as CSSProperties;
  return (
    <ol className={styles.grid} style={gridStyle} aria-label={t("console.dev_compare_grid")}>
      {gridCells(grid).map((cell, index) => (
        <li key={index} className={styles.cell} data-over-limit={cell.overLimit}>
          <span className={styles.value}>{cell.text}</span>
        </li>
      ))}
    </ol>
  );
}
