import { bengaliFont } from "../lib/fonts";
import { theme } from "../lib/theme";

export function LocationBadge({ location }: { location: string }) {
  if (!location) {
    return null;
  }
  return (
    <div
      style={{
        position: "absolute",
        top: 102,
        left: 48,
        padding: "12px 20px",
        borderRadius: 999,
        background: "rgba(7, 11, 20, 0.62)",
        color: theme.paper,
        fontFamily: bengaliFont,
        fontSize: 30,
        letterSpacing: 0.2,
        display: "flex",
        alignItems: "center",
        gap: 10,
        border: "1px solid rgba(246,241,232,0.12)",
      }}
    >
      <span style={{ color: theme.gold }}>📍</span>
      <span>{location}</span>
    </div>
  );
}
