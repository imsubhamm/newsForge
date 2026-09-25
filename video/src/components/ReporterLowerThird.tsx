import { interpolate, useCurrentFrame } from "remotion";

import { bengaliFont } from "../lib/fonts";
import { theme } from "../lib/theme";

export function ReporterLowerThird({ name }: { name: string }) {
  if (!name) {
    return null;
  }
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [28, 42, 110, 128], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        left: 48,
        bottom: 510,
        opacity,
      }}
    >
      <div
        style={{
          background: theme.paper,
          color: theme.navy,
          fontFamily: bengaliFont,
          fontSize: 28,
          padding: "12px 22px",
        }}
      >
        প্রতিবেদন: {name}
      </div>
    </div>
  );
}
