import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

import { bengaliFont } from "../lib/fonts";
import { theme } from "../lib/theme";

export function Outro({ channel = "বাংলা নিউজ" }: { channel?: string }) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const start = durationInFrames - 48;
  const opacity = interpolate(frame, [start, start + 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (frame < start) {
    return null;
  }
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "rgba(7, 11, 20, 0.42)",
        opacity,
      }}
    >
      <div
        style={{
          position: "absolute",
          right: 48,
          bottom: 620,
          color: theme.paper,
          fontFamily: bengaliFont,
          fontSize: 28,
          letterSpacing: 1,
        }}
      >
        {channel}
      </div>
    </div>
  );
}
