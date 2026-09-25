import { Audio, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

import { mediaSrc } from "../lib/media";
import type { TimelineClip } from "../lib/types";

const FADE_MS = 200;

export function ClipAudioTracks({
  clip,
  voiceSrc,
  durationInFrames,
}: {
  clip: TimelineClip;
  voiceSrc?: string;
  durationInFrames: number;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = Math.max(2, Math.round((FADE_MS / 1000) * fps));
  const audio = clip.audio;
  const voiceVolume = audio?.voiceoverEnabled === false ? 0 : (audio?.voiceVolume ?? 1);
  let sourceVolume = audio?.sourceVolume ?? 0;
  if (voiceVolume > 0.4 && sourceVolume > 0.35) {
    sourceVolume = Math.min(sourceVolume, 0.22);
  }

  const faded = (target: number) => {
    if (target <= 0) {
      return 0;
    }
    const fadeIn = interpolate(frame, [0, fade], [0, target], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const fadeOut = interpolate(frame, [durationInFrames - fade, durationInFrames - 1], [target, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return Math.min(fadeIn, fadeOut);
  };

  const voiceStart = audio?.voiceoverStart ?? clip.start;
  const sourceStart = audio?.sourceStart ?? clip.sourceStart;
  const source = audio?.source || clip.src;

  return (
    <>
      {voiceSrc && voiceVolume > 0 ? (
        <Audio src={mediaSrc(voiceSrc)} startFrom={Math.max(0, Math.round(voiceStart * fps))} volume={() => faded(voiceVolume)} />
      ) : null}
      {source && sourceVolume > 0 ? (
        <Audio src={mediaSrc(source)} startFrom={Math.max(0, Math.round(sourceStart * fps))} volume={() => faded(sourceVolume)} />
      ) : null}
    </>
  );
}
