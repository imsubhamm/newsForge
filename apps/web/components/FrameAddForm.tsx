"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { createFrameJob } from "@/lib/api";
import type { AspectRatio } from "@/lib/types";

const VIDEO_ACCEPT = ".mp4,.mov,video/mp4,video/quicktime";

function prettySize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FrameAddForm() {
  const router = useRouter();
  const [aspect, setAspect] = useState<AspectRatio>("16:9");
  const [header, setHeader] = useState("");
  const [footer, setFooter] = useState("");
  const [location, setLocation] = useState("দুর্গাপুর");
  const [video, setVideo] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!video) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(video);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [video]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!video) {
      setError("Choose an MP4 or MOV video.");
      return;
    }
    const form = new FormData();
    form.set("aspect_ratio", aspect);
    form.set("header", header);
    form.set("footer", footer);
    form.set("headline", footer);
    form.set("location", location);
    form.set("video", video);

    setBusy(true);
    setProgress(1);
    try {
      const job = await createFrameJob(form, setProgress);
      router.push(`/frame-add/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-8">
      <fieldset className="space-y-3">
        <legend className="text-sm uppercase tracking-[0.16em] text-[#e4c36a]">Output ratio</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          <RatioCard
            label="16:9 Landscape"
            hint="YouTube · TV · Facebook"
            selected={aspect === "16:9"}
            onClick={() => setAspect("16:9")}
          />
          <RatioCard
            label="9:16 Portrait"
            hint="Reels · Shorts · Stories"
            selected={aspect === "9:16"}
            onClick={() => setAspect("9:16")}
          />
        </div>
      </fieldset>

      <div className="grid gap-6 md:grid-cols-2">
        <label className="block space-y-2">
          <span className="text-sm uppercase tracking-[0.16em] text-[#e4c36a]">Header — top red bar</span>
          <input
            value={header}
            onChange={(e) => setHeader(e.target.value)}
            placeholder="Goes on the top red frame"
            className="field"
          />
        </label>
        <label className="block space-y-2">
          <span className="text-sm uppercase tracking-[0.16em] text-[#e4c36a]">Footer — bottom red bar</span>
          <input
            value={footer}
            onChange={(e) => setFooter(e.target.value)}
            placeholder="Goes on the bottom red frame"
            className="field"
          />
        </label>
        <label className="block space-y-2 md:col-span-2">
          <span className="text-sm uppercase tracking-[0.16em] text-[#e4c36a]">Location plate</span>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Shown next to the pin"
            className="field"
          />
        </label>
      </div>

      <label className="block cursor-pointer rounded-2xl border border-dashed border-[#e4c36a]/30 bg-[#111827]/70 p-4">
        <div className="text-sm uppercase tracking-[0.16em] text-[#e4c36a]">Video</div>
        <div className="mt-1 text-sm text-[#f6f1e8]/55">One MP4 / MOV. The আমার কথা NEWS frame is added automatically.</div>
        <input
          type="file"
          accept={VIDEO_ACCEPT}
          className="mt-4 block w-full text-sm"
          onChange={(event) => setVideo(event.target.files?.[0] ?? null)}
        />
        {video ? (
          <p className="mt-3 text-sm text-[#f6f1e8]/80">
            {video.name} · {prettySize(video.size)}
          </p>
        ) : null}
      </label>

      <FramePreview aspect={aspect} header={header} footer={footer} location={location} previewUrl={previewUrl} />

      {error ? (
        <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</div>
      ) : null}

      {busy ? (
        <div className="space-y-3 rounded-2xl border border-[#e4c36a]/20 bg-black/30 px-4 py-5">
          <div className="flex items-center gap-3">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/15 border-t-[#e4c36a]" />
            <p className="text-sm text-[#e4c36a]">
              {progress < 100 ? `Uploading video… ${progress}%` : "Upload complete. Opening the processing page…"}
            </p>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div className="h-full bg-[#c41e3a] transition-all" style={{ width: `${Math.max(progress, 8)}%` }} />
          </div>
        </div>
      ) : null}

      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-2xl bg-[#c41e3a] px-6 py-4 text-lg font-semibold tracking-wide text-[#f6f1e8] disabled:opacity-60"
      >
        {busy ? "Uploading…" : "Add Frame"}
      </button>
    </form>
  );
}

function RatioCard({
  label,
  hint,
  selected,
  onClick,
}: {
  label: string;
  hint: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-2xl border px-5 py-4 text-left ${
        selected ? "border-[#e4c36a] bg-[#e4c36a]/10" : "border-white/10 bg-white/5"
      }`}
    >
      <div className="text-lg">{label}</div>
      <div className="mt-1 text-sm text-white/55">{hint}</div>
    </button>
  );
}

function FramePreview({
  aspect,
  header,
  footer,
  location,
  previewUrl,
}: {
  aspect: AspectRatio;
  header: string;
  footer: string;
  location: string;
  previewUrl: string | null;
}) {
  const landscape = aspect === "16:9";
  return (
    <div className="space-y-3">
      <p className="text-sm uppercase tracking-[0.16em] text-[#e4c36a]">আমার কথা NEWS frame</p>
      <div className="flex justify-center rounded-3xl border border-[#e4c36a]/15 bg-black/40 p-4">
        <div
          className="relative overflow-hidden bg-[#070B14] shadow-2xl"
          style={{
            width: landscape ? 560 : 240,
            height: landscape ? 318 : 426,
          }}
        >
          {previewUrl ? (
            <video src={previewUrl} className="absolute inset-0 h-full w-full object-cover" muted playsInline />
          ) : (
            <div className="absolute inset-0 bg-[#16b900]/25" />
          )}
          <div className="pointer-events-none absolute inset-0 flex flex-col justify-between">
            <div className="flex items-stretch bg-[#cc1101]">
              <div className="flex min-w-0 flex-1 items-center gap-2 px-2 py-1">
                <span className="text-[16px] leading-none">📍</span>
                <span className="whitespace-nowrap bg-[#ecedee] px-1.5 py-0.5 text-[10px] font-semibold leading-tight text-neutral-800">
                  {location || "দুর্গাপুর"}
                </span>
                <span className="truncate text-[11px] font-semibold text-white">{header}</span>
              </div>
              <div className="shrink-0 border border-[#e4c36a] bg-white px-1.5 py-1 text-center leading-tight">
                <div className="text-[11px] font-bold text-blue-900">আমার</div>
                <div className="text-[11px] font-bold text-red-600">কথা</div>
                <div className="text-[9px] font-bold text-red-600">NEWS</div>
              </div>
            </div>
            <div className="relative">
              <div className="absolute bottom-0 left-0 z-10 border border-[#e4c36a] bg-white px-2 py-1 text-center leading-tight">
                <div className="text-[12px] font-bold text-blue-900">আমার</div>
                <div className="text-[12px] font-bold text-red-600">কথা</div>
              </div>
              <div className="ml-16 bg-[#cc1101] px-3 py-2 text-[11px] text-white">{footer}</div>
              <div className="ml-16 bg-[#e4c000] px-3 py-1 text-[10px] text-red-800">
                খবরের জন্য ফোন করুন 7407897657
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
