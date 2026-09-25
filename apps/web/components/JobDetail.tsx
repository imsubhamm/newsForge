"use client";

import { useEffect, useState } from "react";

import { JobProgress } from "@/components/JobProgress";
import {
  fetchJob,
  fetchSemanticDebug,
  fetchTimeline,
  mediaUrl,
  renderExistingJob,
  setClipAudioMode,
  startJobProcess,
} from "@/lib/api";
import {
  TERMINAL_STATUSES,
  type AudioMode,
  type Job,
  type SemanticDebug,
  type TimelinePlan,
} from "@/lib/types";

const AUDIO_LABEL: Record<AudioMode, string> = {
  VOICEOVER_ONLY: "🎙 VO",
  SOURCE_SOUNDBITE: "🎤 BITE",
  VOICEOVER_WITH_NAT_SOUND: "🔊 NAT",
  NAT_SOUND_ONLY: "🔊 NAT",
};

function formatTime(seconds: number): string {
  const whole = Math.max(0, seconds);
  const mins = Math.floor(whole / 60);
  const secs = (whole % 60).toFixed(1).padStart(4, "0");
  return `${mins}:${secs}`;
}

export function JobDetail({ initial }: { initial: Job }) {
  const [job, setJob] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [debug, setDebug] = useState<SemanticDebug | null>(null);
  const [timeline, setTimeline] = useState<TimelinePlan | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const next = await fetchJob(job.id);
        if (!cancelled) {
          setJob(next);
          if (next.semantic_available) {
            const report = await fetchSemanticDebug(job.id);
            const plan = await fetchTimeline(job.id);
            if (!cancelled) {
              setDebug(report);
              setTimeline(plan);
            }
          }
        }
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
    }, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [job.id, job.status, job.output_url]);

  async function continueJob() {
    setBusy(true);
    try {
      const next = await startJobProcess(job.id);
      setJob(next);
    } finally {
      setBusy(false);
    }
  }

  const canContinue =
    !job.output_url && (job.status === "UPLOADED" || job.status === "ALIGNED" || job.status === "FAILED");
  const continueLabel = job.status === "ALIGNED" ? "Edit and render" : "Analyse voice";

  async function changeAudio(index: number, mode: AudioMode) {
    setBusy(true);
    try {
      const next = await setClipAudioMode(job.id, index, mode);
      setTimeline(next);
    } finally {
      setBusy(false);
    }
  }

  async function rerender() {
    setBusy(true);
    try {
      const next = await renderExistingJob(job.id);
      setJob(next);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <JobProgress status={job.status} steps={job.steps} error={job.error} />

      {canContinue ? (
        <button
          type="button"
          onClick={continueJob}
          disabled={busy}
          className="rounded-xl bg-[#c41e3a] px-5 py-3 text-[#f6f1e8] disabled:opacity-60"
        >
          {busy ? "Starting…" : continueLabel}
        </button>
      ) : null}

      {job.weak_match_count ? (
        <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-amber-100">
          ⚠ Weak footage match on {job.weak_match_count} cut{job.weak_match_count === 1 ? "" : "s"}.
          Review those shots before publishing.
        </p>
      ) : null}
      {job.footage_warning ? <p className="text-sm text-white/55">{job.footage_warning}</p> : null}

      {job.captions.length ? (
        <section className="rounded-3xl border border-[#e4c36a]/15 bg-[#111827]/80 p-6">
          <h2 className="text-xl">Bengali captions</h2>
          <p className="mt-2 text-sm text-white/50">
            Reporter script captions play with voice-over. Soundbite captions play with original speech.
          </p>
          <ol className="mt-4 space-y-3">
            {job.captions.map((cue) => (
              <li key={`${cue.start}-${cue.text}`} className="flex gap-4 text-lg">
                <span className="w-28 shrink-0 text-[#e4c36a]">
                  {formatTime(cue.start)}–{formatTime(cue.end)}
                </span>
                <span>
                  {cue.source === "VIDEO_SOUNDBITE" ? "🎤 " : "🎙 "}
                  {cue.text}
                </span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {debug?.matches.length ? (
        <section className="rounded-3xl border border-white/10 bg-[#111827]/70 p-6">
          <h2 className="text-xl">Semantic edit debug</h2>
          <p className="mt-2 text-sm text-white/50">
            Visual cuts are chosen by meaning. Audio is a separate editorial decision.
          </p>
          <div className="mt-5 space-y-5">
            {debug.matches.map((match) => (
              <div key={match.narration_segment_id}>
                <p className="text-[#e4c36a]">
                  {formatTime(match.start)}–{formatTime(match.end)} · {match.narration_segment_id}
                </p>
                <p className="mt-1 text-lg">{match.text}</p>
                <ul className="mt-2 space-y-1 text-sm text-white/70">
                  {match.candidates.map((candidate) => (
                    <li key={candidate.scene_id}>
                      {candidate.selected ? "→ " : "   "}
                      {candidate.source_file} {candidate.scene_id} {candidate.score.toFixed(2)}
                      {candidate.selected ? " SELECTED" : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {debug?.audio_matches?.length ? (
        <section className="rounded-3xl border border-white/10 bg-[#111827]/70 p-6">
          <h2 className="text-xl">Audio editorial debug</h2>
          <p className="mt-2 text-sm text-white/50">
            The planner chooses voice-over, a soundbite, or natural sound. Two speech tracks never play at full level.
          </p>
          <div className="mt-5 space-y-5">
            {debug.audio_matches.map((match) => (
              <div key={`audio-${match.narration_segment_id}`}>
                <p className="text-[#e4c36a]">
                  {formatTime(match.start)}–{formatTime(match.end)} · {match.mode} · {match.action}
                </p>
                <p className="mt-1 text-lg">{match.text}</p>
                <p className="mt-1 text-sm text-white/55">{match.reason}</p>
                <ul className="mt-2 space-y-1 text-sm text-white/70">
                  {match.candidates.map((candidate) => (
                    <li key={candidate.audio_id}>
                      {candidate.selected ? "→ " : "   "}
                      {candidate.source_file} · {candidate.speaker_type} · {candidate.relevance.toFixed(2)} /{" "}
                      {candidate.quality.toFixed(2)} · {candidate.decision}
                      {candidate.transcript ? ` — “${candidate.transcript}”` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {timeline?.timeline.length ? (
        <section className="rounded-3xl border border-[#e4c36a]/15 bg-[#111827]/80 p-6">
          <h2 className="text-xl">Program timeline</h2>
          <p className="mt-2 text-sm text-white/50">
            VIDEO and AUDIO are independent. Change an audio block, then re-render.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {timeline.timeline.map((clip, index) => (
              <div key={`${clip.start}-${clip.source}`} className="min-w-40 rounded-xl border border-white/10 p-3">
                <div className="text-sm text-[#e4c36a]">
                  {formatTime(clip.start)}–{formatTime(clip.end)}
                </div>
                <div className="mt-1 text-sm text-white/70">{clip.source}</div>
                <div className="mt-2 text-lg">{AUDIO_LABEL[clip.audio.mode]}</div>
                <select
                  className="mt-2 w-full rounded-lg bg-[#070B14] px-2 py-1 text-sm"
                  value={clip.audio.mode}
                  disabled={busy}
                  onChange={(event) => void changeAudio(index, event.target.value as AudioMode)}
                >
                  <option value="VOICEOVER_ONLY">Use Voice-over</option>
                  <option value="SOURCE_SOUNDBITE">Use Original Sound</option>
                  <option value="VOICEOVER_WITH_NAT_SOUND">Voice-over + Natural Sound</option>
                  <option value="NAT_SOUND_ONLY">Mute Voice-over / Nat only</option>
                </select>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => void rerender()}
            disabled={busy}
            className="mt-5 rounded-xl bg-[#c41e3a] px-5 py-3 text-[#f6f1e8] disabled:opacity-60"
          >
            {busy ? "Working…" : "Re-render with audio edits"}
          </button>
        </section>
      ) : null}

      <section className="rounded-3xl border border-white/10 bg-[#111827]/70 p-6">
        <h2 className="text-xl">Stored assets</h2>
        <ul className="mt-4 space-y-2 text-white/75">
          {job.assets.map((asset) => (
            <li key={`${asset.kind}-${asset.path}`}>
              <span className="text-[#e4c36a]">{asset.kind}</span> · {asset.path}
            </li>
          ))}
        </ul>
      </section>

      {job.output_url ? (
        <section className="space-y-4 rounded-3xl border border-[#e4c36a]/20 bg-[#111827]/80 p-6">
          <h2 className="text-3xl">News video ready</h2>
          <video
            className="mx-auto h-[640px] w-[360px] rounded-2xl bg-black object-cover"
            src={mediaUrl(job.output_url)}
            controls
            playsInline
            preload="metadata"
          />
          <a
            href={mediaUrl(job.output_url)}
            download
            className="inline-block rounded-xl bg-[#c41e3a] px-5 py-3 text-[#f6f1e8]"
          >
            Download Video
          </a>
        </section>
      ) : (
        <p className="text-white/50">
          {job.status === "RENDERING"
            ? "Rendering the 1080×1920 reel. This can take a few minutes."
            : "A rendered reel will appear here after editing finishes."}
        </p>
      )}
    </div>
  );
}
