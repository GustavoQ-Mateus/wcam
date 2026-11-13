import type { StageMedian } from "../data/dev-view";
import type { MessageKey } from "../data/i18n";
import { t } from "../data/language";
import styles from "./dev.module.scss";

interface FramePathProps {
  stages: StageMedian[];
  streamingApps: number | null;
}

const STAGE_KEYS: Readonly<Record<StageMedian["stage"], MessageKey>> = {
  phone: "dev.stage_phone",
  wifi: "dev.stage_wifi",
  decode: "dev.stage_decode",
  color: "dev.stage_color",
  deliver: "dev.stage_deliver",
  apps: "dev.stage_apps",
};
const MS_DECIMALS = 1;

export function FramePath({ stages, streamingApps }: FramePathProps) {
  return (
    <ol className={styles.path}>
      {stages.map(({ stage, milliseconds }) => (
        <li key={stage} className={styles.pathStep}>
          <span className={styles.pathName}>{t(STAGE_KEYS[stage])}</span>
          <span className={styles.pathValue} data-empty={milliseconds === null && stage !== "apps"}>
            {stageValue(stage, milliseconds, streamingApps)}
          </span>
        </li>
      ))}
    </ol>
  );
}

function stageValue(stage: StageMedian["stage"], milliseconds: number | null, streamingApps: number | null): string {
  if (stage === "apps") {
    return streamingApps === null ? t("dev.not_reported") : String(streamingApps);
  }
  return milliseconds === null
    ? t("dev.not_reported")
    : t("dev.milliseconds", { value: milliseconds.toFixed(MS_DECIMALS) });
}
