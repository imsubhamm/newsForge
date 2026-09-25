import { interpolate, useCurrentFrame } from "remotion";

import { bengaliFont } from "../lib/fonts";
import { theme } from "../lib/theme";

export function BreakingNewsBanner() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12, 68, 82], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        top: 214,
        left: 48,
        opacity,
        display: "flex",
        alignItems: "center",
        gap: 0,
        boxShadow: "0 12px 40px rgba(0,0,0,0.28)",
      }}
    >
      <div
        style={{
          background: theme.red,
          color: theme.paper,
          fontFamily: bengaliFont,
          fontWeight: 700,
          fontSize: 24,
          letterSpacing: 2,
          padding: "10px 16px",
        }}
      >
        BREAKING
      </div>
      <div
        style={{
          background: theme.ink,
          color: theme.paper,
          fontFamily: bengaliFont,
          fontSize: 24,
          padding: "10px 18px",
        }}
      >
        বিশেষ সংবাদ
      </div>
    </div>
  );
}
