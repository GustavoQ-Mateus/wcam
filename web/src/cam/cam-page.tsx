import { useState } from "react";
import { isLive } from "../data/cam-state";
import { takePairingTokenFromLocation } from "../data/pairing";
import { isMirrored } from "../media/capture";
import styles from "./cam-page.module.scss";
import { isMessageState } from "./cam-messages";
import { LiveLayer } from "./live-layer";
import { MessageLayer } from "./message-layer";
import { useCam } from "./use-cam";
import { Viewfinder } from "./viewfinder";

const PAIRING_TOKEN = takePairingTokenFromLocation();

export default function CamPage() {
  const cam = useCam(PAIRING_TOKEN !== null);
  const [noticeDismissed, setNoticeDismissed] = useState(false);
  const { state } = cam;

  return (
    <main className={styles.page}>
      <Viewfinder videoRef={cam.videoRef} mirrored={isMirrored(cam.facing)} visible={isLive(state) && !cam.switching} />
      {isLive(state) ? (
        <LiveLayer
          state={state}
          showNotice={cam.wakeLockUnavailable && !noticeDismissed}
          onDismissNotice={() => {
            setNoticeDismissed(true);
          }}
          onSwitchCamera={cam.switchCamera}
          onTogglePreview={cam.togglePreview}
        />
      ) : (
        isMessageState(state) && <MessageLayer state={state} onStart={cam.start} />
      )}
    </main>
  );
}
