import { useState } from "react";

const TIME_FORMAT: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit", second: "2-digit" };

export function useFrozenSince(frozen: boolean, observedAt: number, language: string): string | null {
  const [since, setSince] = useState<number | null>(null);
  if (frozen && since === null) {
    setSince(observedAt);
  }
  if (!frozen && since !== null) {
    setSince(null);
  }
  return since === null ? null : new Date(since).toLocaleTimeString(language, TIME_FORMAT);
}
