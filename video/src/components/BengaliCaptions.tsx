import { useCurrentFrame, useVideoConfig } from "remotion";

import { bengaliFont } from "../lib/fonts";
import type { CaptionCue } from "../lib/types";

export function BengaliCaptions({ captions }: { captions: CaptionCue[] }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;
  const active = captions.find((cue) => time >= cue.start && time < cue.end);

  if (!active) {
    return null;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: 48,
        right: 48,
        bottom: 132,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          maxWidth: 980,
          padding: "14px 18px",
          borderRadius: 16,
          background: "rgba(7, 11, 20, 0.72)",
          color: "#F6F1E8",
          fontFamily: bengaliFont,
          fontSize: 36,
          lineHeight: 1.3,
          textAlign: "center",
          textShadow: "0 2px 10px rgba(0,0,0,0.65)",
        }}
      >
        {active.text}
      </div>
    </div>
  );
}
