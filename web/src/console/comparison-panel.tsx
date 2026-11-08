import { comparisonImageUrl } from "../data/api-client";
import { captureTime, reportDataUrl } from "../data/comparison-format";
import type { Comparison } from "../data/contract";
import { errorMessageKey } from "../data/i18n";
import { t } from "../data/language";
import { ComparisonImage } from "./comparison-image";
import styles from "./comparison-panel.module.scss";
import { DifferenceDetails } from "./difference-details";
import { DownloadLink } from "./download-link";
import { ScreenInput } from "./screen-input";
import type { ComparisonView, ScreenUpload } from "./use-comparison";

interface ComparisonPanelProps {
  view: ComparisonView;
  onAddScreen: (file: File) => void;
}

const VERSUS = " / ";

export function ComparisonPanel({ view, onAddScreen }: ComparisonPanelProps) {
  if (view.kind === "idle") {
    return null;
  }
  return (
    <section className={styles.panel} aria-label={t("console.dev_compare")}>
      {view.kind === "pending" && (
        <p className={styles.pending} role="status">
          <span className={styles.pendingMark} aria-hidden="true" />
          {t("console.dev_compare_pending")}
        </p>
      )}
      {view.kind === "failed" && <FailedLine text={t("console.dev_compare_failed", { reason: view.reason })} />}
      {view.kind === "ready" && (
        <ReadyComparison
          comparison={view.comparison}
          pcImageUrl={view.pcImageUrl}
          screen={view.screen}
          onAddScreen={onAddScreen}
        />
      )}
    </section>
  );
}

interface ReadyComparisonProps {
  comparison: Comparison;
  pcImageUrl: string | null;
  screen: ScreenUpload;
  onAddScreen: (file: File) => void;
}

function ReadyComparison({ comparison, pcImageUrl, screen, onAddScreen }: ReadyComparisonProps) {
  const { id, phone, pc, difference, screenDifference } = comparison;
  const phoneUrl = comparisonImageUrl(id, "phone");
  const screenUrl = comparisonImageUrl(id, "screen");
  const phoneName = t("console.dev_compare_phone");
  const pcName = t("console.dev_compare_pc");
  const screenName = t("console.dev_compare_screen_label");
  return (
    <>
      <div className={styles.images}>
        {phone && (
          <ComparisonImage
            label={phoneName}
            time={captureTime(phone.capturedAt)}
            src={phoneUrl}
            width={phone.width}
            height={phone.height}
          />
        )}
        {pc && pcImageUrl && (
          <ComparisonImage
            label={pcName}
            time={captureTime(pc.receivedAt)}
            src={pcImageUrl}
            width={pc.width}
            height={pc.height}
            grid={difference?.grid}
          />
        )}
        {comparison.screen && (
          <ComparisonImage
            label={screenName}
            time={captureTime(comparison.screen.receivedAt)}
            src={screenUrl}
            width={comparison.screen.width}
            height={comparison.screen.height}
          />
        )}
      </div>
      <div className={styles.detailGroups}>
        {difference && <DifferenceDetails title={`${phoneName}${VERSUS}${pcName}`} difference={difference} />}
        {screenDifference && (
          <>
            <DifferenceDetails title={`${screenName}${VERSUS}${phoneName}`} difference={screenDifference.phone} />
            <DifferenceDetails title={`${screenName}${VERSUS}${pcName}`} difference={screenDifference.pc} />
          </>
        )}
      </div>
      <div className={styles.actions}>
        <DownloadLink href={phoneUrl} fileName={`wcam-${id}-phone.png`}>
          {t("console.dev_compare_download_phone")}
        </DownloadLink>
        {pcImageUrl && (
          <DownloadLink href={pcImageUrl} fileName={`wcam-${id}-pc.png`}>
            {t("console.dev_compare_download_pc")}
          </DownloadLink>
        )}
        {comparison.screen && (
          <DownloadLink href={screenUrl} fileName={`wcam-${id}-screen.png`}>
            {t("console.dev_compare_download_screen")}
          </DownloadLink>
        )}
        <DownloadLink href={reportDataUrl(comparison)} fileName={`wcam-${id}.json`}>
          {t("console.dev_compare_download_report")}
        </DownloadLink>
      </div>
      {!comparison.screen && <ScreenInput sending={screen.kind === "sending"} onFile={onAddScreen} />}
      {screen.kind === "failed" && <FailedLine text={t(errorMessageKey(screen.code))} />}
    </>
  );
}

function FailedLine({ text }: { text: string }) {
  return (
    <p className={styles.failed} role="alert">
      <span className={styles.failedMark} aria-hidden="true" />
      {text}
    </p>
  );
}
