import { Composition } from "remotion";

import { NewsVideo } from "./compositions/NewsVideo";
import { defaultNewsProps, type NewsVideoProps } from "./lib/types";

export const RemotionRoot = () => {
  return (
    <Composition
      id="NewsVideo"
      component={NewsVideo}
      durationInFrames={240}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultNewsProps}
      calculateMetadata={async ({ props }: { props: NewsVideoProps }) => ({
        durationInFrames: Math.max(30, Math.round((props.duration || 8) * 30)),
        fps: 30,
        width: 1080,
        height: 1920,
      })}
    />
  );
};
