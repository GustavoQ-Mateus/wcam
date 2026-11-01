const CONFIRMATION_DOMAIN = "wcam-confirmation-v1";
const ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ";
const ALPHABET_SIZE = BigInt(ALPHABET.length);
const CODE_LENGTH = 6;
const GROUP_LENGTH = 3;
const FINGERPRINT_PATTERN = /^a=fingerprint:sha-256 (\S+)\s*$/im;

export async function confirmationCode(
  nonce: string,
  phoneFingerprint: string,
  agentFingerprint: string,
): Promise<string> {
  const message = [CONFIRMATION_DOMAIN, nonce, phoneFingerprint, agentFingerprint].join("|");
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(message));
  let value = new DataView(digest).getBigUint64(0, false);
  let symbols = "";
  for (let index = 0; index < CODE_LENGTH; index++) {
    symbols += ALPHABET.charAt(Number(value % ALPHABET_SIZE));
    value /= ALPHABET_SIZE;
  }
  return `${symbols.slice(0, GROUP_LENGTH)}-${symbols.slice(GROUP_LENGTH)}`;
}

export function sdpFingerprint(sdp: string): string | null {
  return FINGERPRINT_PATTERN.exec(sdp)?.[1]?.toUpperCase() ?? null;
}
