import { useEffect, useState } from "react";

export interface ImageSize {
  width: number;
  height: number;
}

export function useImageSize(url: string): ImageSize | null {
  const [size, setSize] = useState<{ url: string; size: ImageSize } | null>(null);

  useEffect(() => {
    const image = new Image();
    let current = true;
    image.addEventListener("load", () => {
      if (current) {
        setSize({ url, size: { width: image.naturalWidth, height: image.naturalHeight } });
      }
    });
    image.src = url;
    return () => {
      current = false;
    };
  }, [url]);

  return size?.url === url ? size.size : null;
}
