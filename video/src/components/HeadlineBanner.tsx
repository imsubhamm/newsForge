import { bengaliFont } from "../lib/fonts";
import { theme } from "../lib/theme";

export function headlineLines(headline: string): string[] {
  const trimmed = headline.trim();
  if (!trimmed) {
    return [];
  }
  const parts = trimmed.split(/(?<=[,،।])\s+/).map((part) => part.trim()).filter(Boolean);
  if (parts.length >= 2 && trimmed.length > 32) {
    return [parts[0], parts.slice(1).join(" ")];
  }
  return [trimmed];
}

export function headlineFontSize(headline: string, lines: number): number {
  const length = Math.max(...headlineLines(headline).map((line) => line.length), headline.length);
  if (lines >= 2) {
    return length > 36 ? 34 : 38;
  }
  if (length <= 22) return 46;
  if (length <= 36) return 38;
  return 32;
}

export function HeadlineBanner({ headline }: { headline: string }) {
  const lines = headlineLines(headline);
  const fontSize = headlineFontSize(headline, lines.length);

  return (
    <div
      style={{
        position: "absolute",
        left: 32,
        right: 32,
        bottom: 268,
        width: 1016,
        maxHeight: 230,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: 72,
          height: 5,
          background: theme.red,
          marginBottom: 10,
        }}
      />
      <div
        style={{
          background: "rgba(7, 11, 20, 0.82)",
          padding: "16px 20px",
          borderLeft: `6px solid ${theme.gold}`,
        }}
      >
        {lines.map((line) => (
          <div
            key={line}
            style={{
              fontFamily: bengaliFont,
              fontWeight: 700,
              fontSize,
              lineHeight: 1.3,
              color: theme.paper,
              whiteSpace: "normal",
              overflowWrap: "break-word",
              wordBreak: "break-word",
            }}
          >
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}
