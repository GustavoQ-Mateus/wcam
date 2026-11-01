export interface Address {
  pathname: string;
  search: string;
  hash: string;
}

const PAIRING_FRAGMENT_PATTERN = /^#t=(.+)$/;

let pendingToken: string | null = null;

export function takePairingToken(address: Address, replaceAddress: (url: string) => void): string | null {
  const token = PAIRING_FRAGMENT_PATTERN.exec(address.hash)?.[1];
  if (token === undefined) {
    return null;
  }
  replaceAddress(`${address.pathname}${address.search}`);
  return token;
}

export function storePairingTokenFromLocation(): boolean {
  pendingToken = takePairingToken(window.location, (url) => {
    window.history.replaceState(window.history.state, "", url);
  });
  return pendingToken !== null;
}

export function consumePairingToken(): string | null {
  const token = pendingToken;
  pendingToken = null;
  return token;
}
