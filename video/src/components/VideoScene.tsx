import { OffthreadVideo } from "remotion";

import type { CropMode } from "../lib/types";

type Props = {
  src: string;
  sourceStart: number;
  sourceEnd: number;
  fps: number;
  cropMode: CropMode;
};

export function VideoScene({ src, sourceStart, sourceEnd, fps, cropMode }: Props) {
  const startFrom = Math.max(0, Math.round(sourceStart * fps));
  const endAt = Math.max(startFrom + 1, Math.round(sourceEnd * fps));

  if (cropMode === "blur-background") {
    return (
      <div style={{ position: "absolute", inset: 0, background: "#070B14" }}>
        <OffthreadVideo
          src={src}
          startFrom={startFrom}
          endAt={endAt}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "blur(28px) brightness(0.45) saturate(0.9)",
            transform: "scale(1.12)",
          }}
        />
        <OffthreadVideo
          src={src}
          startFrom={startFrom}
          endAt={endAt}
          muted
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "contain",
          }}
        />
      </div>
    );
  }

  return (
    <OffthreadVideo
      src={src}
      startFrom={startFrom}
      endAt={endAt}
      muted
      style={{
        width: "100%",
        height: "100%",
        objectFit: cropMode === "fit" ? "contain" : "cover",
        background: "#070B14",
      }}
    />
  );
}
