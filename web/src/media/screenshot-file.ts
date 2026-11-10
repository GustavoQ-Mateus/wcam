import { isPng } from "../data/snapshot";

export async function readPngFile(file: File): Promise<Uint8Array | null> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  return isPng(bytes) ? bytes : null;
}
