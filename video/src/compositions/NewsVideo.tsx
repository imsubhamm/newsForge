import { useEffect } from "react";
import { AbsoluteFill, Audio, Sequence, useVideoConfig } from "remotion";

import { BengaliCaptions } from "../components/BengaliCaptions";
import { BreakingNewsBanner } from "../components/BreakingNewsBanner";
import { ChannelLogo } from "../components/ChannelLogo";
import { HeadlineBanner } from "../components/HeadlineBanner";
import { LocationBadge } from "../components/LocationBadge";
import { Outro } from "../components/Outro";
import { ReporterLowerThird } from "../components/ReporterLowerThird";
import { VideoScene } from "../components/VideoScene";
import { loadBengaliFonts } from "../lib/fonts";
import { mediaSrc } from "../lib/media";
import type { NewsVideoProps } from "../lib/types";

export function NewsVideo({
  headline,
  location,
  reporterName,
  cropMode,
  audioSrc,
  logoSrc,
  clips,
  captions,
}: NewsVideoProps) {
  const { fps } = useVideoConfig();

  useEffect(() => {
    void loadBengaliFonts();
  }, []);

  return (
    <AbsoluteFill style={{ background: "#070B14" }}>
      {clips.map((clip) => {
        const from = Math.round(clip.start * fps);
        const durationInFrames = Math.max(1, Math.round((clip.end - clip.start) * fps));
        return (
          <Sequence key={`${clip.src}-${clip.start}`} from={from} durationInFrames={durationInFrames}>
            <VideoScene
              src={mediaSrc(clip.src)}
              sourceStart={clip.sourceStart}
              sourceEnd={clip.sourceEnd}
              fps={fps}
              cropMode={clip.cropMode ?? cropMode}
            />
          </Sequence>
        );
      })}

      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(7,11,20,0.38) 0%, rgba(7,11,20,0.08) 22%, rgba(7,11,20,0.08) 58%, rgba(7,11,20,0.78) 100%)",
        }}
      />

      <LocationBadge location={location} />
      <ChannelLogo src={logoSrc ? mediaSrc(logoSrc) : mediaSrc("/logo/channel.png")} />
      <BreakingNewsBanner />
      <ReporterLowerThird name={reporterName} />
      <HeadlineBanner headline={headline} />
      <BengaliCaptions captions={captions} />
      <Outro />

      {audioSrc ? <Audio src={mediaSrc(audioSrc)} volume={1} /> : null}
    </AbsoluteFill>
  );
}
