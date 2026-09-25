import { continueRender, delayRender, staticFile } from "remotion";

let loaded = false;

export async function loadBengaliFonts(): Promise<void> {
  if (loaded || typeof document === "undefined") {
    return;
  }
  const handle = delayRender("Loading Noto Sans Bengali");
  const faces = [
    new FontFace(
      "Noto Sans Bengali",
      `url(${staticFile("fonts/NotoSansBengali-Regular.ttf")}) format("truetype")`,
      { weight: "400", style: "normal" },
    ),
    new FontFace(
      "Noto Sans Bengali",
      `url(${staticFile("fonts/NotoSansBengali-Bold.ttf")}) format("truetype")`,
      { weight: "700", style: "normal" },
    ),
  ];
  await Promise.all(
    faces.map(async (face) => {
      const ready = await face.load();
      document.fonts.add(ready);
    }),
  );
  loaded = true;
  continueRender(handle);
}

export const bengaliFont = "Noto Sans Bengali, sans-serif";
