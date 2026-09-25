import { STEP_LABELS } from "@/lib/types";

export function JobProgress({
  status,
  steps,
  error,
}: {
  status: string;
  steps: Record<string, boolean>;
  error: string | null;
}) {
  return (
    <section className="rounded-3xl border border-[#e4c36a]/15 bg-[#111827]/80 p-6">
      <p className="text-sm uppercase tracking-[0.18em] text-[#e4c36a]">{status}</p>
      <h2 className="mt-2 text-2xl">Creating your news reel...</h2>
      <ol className="mt-6 space-y-3">
        {Object.entries(STEP_LABELS).map(([key, label]) => {
          const done = Boolean(steps[key]);
          return (
            <li key={key} className="flex items-center gap-3 text-lg">
              <span className={done ? "text-emerald-400" : "text-white/25"}>{done ? "✓" : "○"}</span>
              <span className={done ? "text-[#f6f1e8]" : "text-white/40"}>{label}</span>
            </li>
          );
        })}
      </ol>
      {error ? (
        <p className="mt-6 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-red-100">{error}</p>
      ) : null}
    </section>
  );
}
