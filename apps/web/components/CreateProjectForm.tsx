"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { createJob } from "@/lib/api";

const AUDIO_ACCEPT = ".mp3,.wav,.m4a,audio/mpeg,audio/wav";
const VIDEO_ACCEPT = ".mp4,.mov,video/mp4,video/quicktime";
const LOGO_ACCEPT = ".png,.jpg,.jpeg,.webp,.svg,image/png,image/jpeg";

function prettySize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function CreateProjectForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [reporterName, setReporterName] = useState("");
  const [script, setScript] = useState("");
  const [voice, setVoice] = useState<File | null>(null);
  const [footage, setFootage] = useState<File[]>([]);
  const [logo, setLogo] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const footageLabel = useMemo(() => {
    if (!footage.length) return "No clips selected";
    const total = footage.reduce((sum, file) => sum + file.size, 0);
    return `${footage.length} clip${footage.length === 1 ? "" : "s"} · ${prettySize(total)}`;
  }, [footage]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!voice) {
      setError("Upload a Bengali voice-over (MP3, WAV, or M4A).");
      return;
    }
    if (!footage.length) {
      setError("Upload at least one MP4 or MOV clip.");
      return;
    }
    const form = new FormData();
    form.set("title", title);
    form.set("location", location);
    form.set("reporter_name", reporterName);
    form.set("script", script);
    form.set("voice", voice);
    footage.forEach((file) => form.append("footage", file));
    if (logo) form.set("logo", logo);

    setBusy(true);
    setProgress(1);
    try {
      const job = await createJob(form, setProgress);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <Field label="News Title">
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="দুর্গাপুরের মলে হঠাৎ হনুমান"
          className="field"
        />
      </Field>
      <div className="grid gap-6 md:grid-cols-2">
        <Field label="Location">
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="দুর্গাপুর"
            className="field"
          />
        </Field>
        <Field label="Reporter Name">
          <input
            value={reporterName}
            onChange={(e) => setReporterName(e.target.value)}
            placeholder="রিয়া সেন"
            className="field"
          />
        </Field>
      </div>
      <Field label="Bengali Script">
        <textarea
          required
          value={script}
          onChange={(e) => setScript(e.target.value)}
          rows={8}
          placeholder="খবরের মূল স্ক্রিপ্ট এখানে লিখুন..."
          className="field min-h-48 resize-y"
        />
      </Field>

      <div className="grid gap-6 md:grid-cols-3">
        <UploadBox
          label="Voiceover"
          hint="MP3 / WAV / M4A"
          accept={AUDIO_ACCEPT}
          multiple={false}
          files={voice ? [voice] : []}
          onFiles={(files) => setVoice(files[0] ?? null)}
        />
        <UploadBox
          label="Raw Footage"
          hint="Multiple MP4 / MOV"
          accept={VIDEO_ACCEPT}
          multiple
          files={footage}
          onFiles={setFootage}
        />
        <UploadBox
          label="Channel Logo"
          hint="Optional PNG / JPG"
          accept={LOGO_ACCEPT}
          multiple={false}
          files={logo ? [logo] : []}
          onFiles={(files) => setLogo(files[0] ?? null)}
        />
      </div>
      <p className="text-sm text-[#f6f1e8]/60">{footageLabel}</p>

      {error ? (
        <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      ) : null}

      {busy ? (
        <div className="space-y-2">
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div className="h-full bg-[#c41e3a] transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="text-sm text-[#e4c36a]">Uploading assets… {progress}%</p>
        </div>
      ) : null}

      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-2xl bg-[#c41e3a] px-6 py-4 text-lg font-semibold tracking-wide text-[#f6f1e8] disabled:opacity-60"
      >
        {busy ? "Creating project…" : "Create Project"}
      </button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-sm uppercase tracking-[0.16em] text-[#e4c36a]">{label}</span>
      {children}
    </label>
  );
}

function UploadBox({
  label,
  hint,
  accept,
  multiple,
  files,
  onFiles,
}: {
  label: string;
  hint: string;
  accept: string;
  multiple: boolean;
  files: File[];
  onFiles: (files: File[]) => void;
}) {
  return (
    <label className="block cursor-pointer rounded-2xl border border-dashed border-[#e4c36a]/30 bg-[#111827]/70 p-4">
      <div className="text-sm uppercase tracking-[0.16em] text-[#e4c36a]">{label}</div>
      <div className="mt-1 text-sm text-[#f6f1e8]/55">{hint}</div>
      <input
        type="file"
        accept={accept}
        multiple={multiple}
        className="mt-4 block w-full text-sm"
        onChange={(event) => onFiles(Array.from(event.target.files ?? []))}
      />
      <ul className="mt-3 space-y-1 text-sm text-[#f6f1e8]/80">
        {files.map((file) => (
          <li key={file.name}>
            {file.name} · {prettySize(file.size)}
          </li>
        ))}
      </ul>
    </label>
  );
}
