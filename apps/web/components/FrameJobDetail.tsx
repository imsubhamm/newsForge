"use client";

import { useEffect, useState } from "react";

import { fetchFrameJob, mediaUrl } from "@/lib/api";
import { TERMINAL_STATUSES, type FrameJob } from "@/lib/types";

export function FrameJobDetail({ initial }: { initial: FrameJob }) {
  const [job, setJob] = useState(initial);
  const [playable, setPlayable] = useState(false);
  const [videoKey, setVideoKey] = useState(0);

  const failed = job.status === "FAILED";
  const outputUrl = job.status === "COMPLETED" ? job.output_url : null;
  const ready = Boolean(outputUrl) && playable;

  useEffect(() => {
    setPlayable(false);
  }, [job.output_url, job.status]);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const next = await fetchFrameJob(job.id);
        if (!cancelled) setJob(next);
      } catch {
        /* keep last known state */
      }
    }
    void refresh();
    if (TERMINAL_STATUSES.has(job.status) && job.output_url) {
      return () => {
        cancelled = true;
      };
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [job.id, job.status, job.output_url]);

  const landscape = job.aspect_ratio === "16:9";
  const playerStyle = landscape ? { width: 720, maxWidth: "100%", height: 405 } : { width: 360, maxWidth: "100%", height: 640 };

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-[#e4c36a]/15 bg-[#111827]/80 p-6">
        <p className="text-sm uppercase tracking-[0.18em] text-[#e4c36a]">
          {ready ? "COMPLETED" : failed ? "FAILED" : job.status === "RENDERING" ? "RENDERING" : "PROCESSING"}
        </p>
        <h2 className="mt-2 text-2xl">{job.aspect_ratio} news frame</h2>
        <p className="mt-2 text-white/60">
          {job.header || job.footer || job.headline || "আমার কথা NEWS"} · {job.location || job.channel_name} · {job.width}×{job.height}
        </p>
        {job.error ? (
          <p className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-red-100">{job.error}</p>
        ) : null}
      </section>

      <section className="space-y-4 rounded-3xl border border-[#e4c36a]/20 bg-[#111827]/80 p-6">
        <h2 className="text-3xl">{ready ? "Framed video ready" : failed ? "Could not add the frame" : "Adding news frame"}</h2>

        {!failed ? (
          <div className="relative mx-auto overflow-hidden rounded-2xl bg-black" style={playerStyle}>
            {outputUrl ? (
              <video
                key={`${outputUrl}-${videoKey}`}
                className={`h-full w-full bg-black object-contain ${ready ? "" : "opacity-0"}`}
                src={mediaUrl(outputUrl)}
                controls={ready}
                playsInline
                preload="auto"
                onLoadedMetadata={(event) => {
                  if (event.currentTarget.duration > 0.2) {
                    setPlayable(true);
                  }
                }}
                onCanPlay={() => setPlayable(true)}
                onError={() => {
                  setPlayable(false);
                  window.setTimeout(() => setVideoKey((value) => value + 1), 2500);
                }}
              />
            ) : null}
            {!ready ? <FrameLoadingOverlay status={job.status} hasFile={Boolean(outputUrl)} /> : null}
          </div>
        ) : null}

        {ready && outputUrl ? (
          <a
            href={`${outputUrl}?download=1`}
            download="framed.mp4"
            className="inline-block rounded-xl bg-[#c41e3a] px-5 py-3 text-[#f6f1e8]"
          >
            Download framed video
          </a>
        ) : null}
      </section>
    </div>
  );
}

function FrameLoadingOverlay({ status, hasFile }: { status: string; hasFile: boolean }) {
  const message =
    status === "RENDERING"
      ? "Burning the আমার কথা NEWS banner onto your video…"
      : hasFile
        ? "Finishing the file so it can play and download…"
        : "Queued. Adding the news frame now…";
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-[#070B14] px-6 text-center">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-white/15 border-t-[#e4c36a]" />
      <p className="text-lg text-[#f6f1e8]">{message}</p>
      <p className="text-sm text-white/50">Download appears only after the framed video is ready.</p>
      <div className="h-1.5 w-48 overflow-hidden rounded-full bg-white/10">
        <div className="h-full w-1/2 animate-pulse bg-[#c41e3a]" />
      </div>
    </div>
  );
}
