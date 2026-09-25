import { staticFile } from "remotion";

export function mediaSrc(src: string): string {
  if (!src) {
    return src;
  }
  if (/^(https?:|data:|blob:)/.test(src)) {
    return src;
  }
  return staticFile(src.replace(/^\//, ""));
}
