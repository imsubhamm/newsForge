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
  const wantVoice = audio?.mode !== "SOURCE_SOUNDBITE" && audio?.mode !== "NAT_SOUND_ONLY" && audio?.voiceoverEnabled !== false;
  const voiceVolume = wantVoice ? (audio?.voiceVolume ?? 1) : 0;
  const sourceVolume = voiceVolume > 0 ? 0 : (audio?.sourceVolume ?? 0);

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
