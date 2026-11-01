import { resolveLanguage, translate, type MessageKey, type MessageValues } from "./i18n";

export const LANGUAGE = resolveLanguage(navigator.language);

export function t(key: MessageKey, values?: MessageValues): string {
  return translate(LANGUAGE, key, values);
}
