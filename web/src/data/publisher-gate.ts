export interface GateOutputs<Track> {
  replaceTrack: (track: Track | null) => void;
  send: (data: string) => void;
}

export interface PublisherGate<Track> {
  readonly live: boolean;
  setTrack: (track: Track | null) => void;
  goLive: () => void;
  send: (data: string) => void;
  confirmCode: () => void;
  rejectCode: () => void;
}

const CONFIRM_CODE_MESSAGE = JSON.stringify({ type: "confirm_code" });
const REJECT_CODE_MESSAGE = JSON.stringify({ type: "reject_code" });

export function createPublisherGate<Track>({ replaceTrack, send }: GateOutputs<Track>): PublisherGate<Track> {
  let live = false;
  let answered = false;
  let track: Track | null = null;
  const answer = (message: string) => {
    if (live || answered) {
      return;
    }
    answered = true;
    send(message);
  };
  return {
    get live() {
      return live;
    },
    setTrack: (nextTrack) => {
      if (nextTrack === track) {
        return;
      }
      track = nextTrack;
      if (live) {
        replaceTrack(track);
      }
    },
    goLive: () => {
      if (live) {
        return;
      }
      live = true;
      if (track !== null) {
        replaceTrack(track);
      }
    },
    send: (data) => {
      if (live) {
        send(data);
      }
    },
    confirmCode: () => {
      answer(CONFIRM_CODE_MESSAGE);
    },
    rejectCode: () => {
      answer(REJECT_CODE_MESSAGE);
    },
  };
}
