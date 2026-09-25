export type CropMode = "center-crop" | "blur-background" | "fit";

export type TimelineClip = {
  start: number;
  end: number;
  src: string;
  sourceStart: number;
  sourceEnd: number;
  cropMode?: CropMode;
};

export type CaptionCue = {
  start: number;
  end: number;
  text: string;
};

export type NewsVideoProps = {
  headline: string;
  location: string;
  reporterName: string;
  duration: number;
  cropMode: CropMode;
  audioSrc: string;
  bedSrc?: string | null;
  logoSrc?: string | null;
  clips: TimelineClip[];
  captions: CaptionCue[];
};

export const defaultNewsProps: NewsVideoProps = {
  headline: "দুর্গাপুরের মলে হঠাৎ হনুমান",
  location: "দুর্গাপুর",
  reporterName: "রিয়া সেন",
  duration: 8,
  cropMode: "center-crop",
  audioSrc: "",
  bedSrc: null,
  logoSrc: "/logo/channel.png",
  clips: [],
  captions: [],
};
