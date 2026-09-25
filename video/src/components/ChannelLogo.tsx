import { Img } from "remotion";

import { bengaliFont } from "../lib/fonts";
import { theme } from "../lib/theme";

export function ChannelLogo({ src }: { src?: string | null }) {
  return (
    <div
      style={{
        position: "absolute",
        top: 42,
        right: 36,
        zIndex: 40,
        width: 148,
        height: 148,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {src ? (
        <Img
          src={src}
          style={{
            width: 148,
            height: 148,
            objectFit: "contain",
            borderRadius: "50%",
            background: "transparent",
            boxShadow: "0 14px 36px rgba(0,0,0,0.45)",
          }}
        />
      ) : (
        <div
          style={{
            width: 132,
            height: 132,
            borderRadius: "50%",
            background: `linear-gradient(160deg, ${theme.red}, ${theme.redDeep})`,
            color: theme.paper,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: bengaliFont,
            fontWeight: 700,
            fontSize: 28,
            letterSpacing: 1,
          }}
        >
          BN
        </div>
      )}
    </div>
  );
}
