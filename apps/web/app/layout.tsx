import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Bangla News AI Editor",
  description: "Local-first AI editor for Bengali news reels",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="bn">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="mx-auto min-h-screen max-w-5xl px-5 py-10">{children}</div>
      </body>
    </html>
  );
}
