import { CreateProjectForm } from "@/components/CreateProjectForm";
import { fetchJobs } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const jobs = await fetchJobs().catch(() => []);

  return (
    <main className="space-y-10">
      <header className="space-y-3">
        <p className="text-sm uppercase tracking-[0.28em] text-[#e4c36a]">Bengali newsroom</p>
        <h1 className="text-4xl font-semibold leading-tight md:text-6xl">Bangla News AI Editor</h1>
        <p className="max-w-2xl text-lg text-[#f6f1e8]/70">
          Upload a script, voice-over, and raw footage. The editor builds a vertical news reel for
          Instagram, Facebook, and YouTube Shorts — you approve before anything is published.
        </p>
        <p className="text-sm text-white/55">
          Need a banner and footer on an already-cut video?{" "}
          <a href="/frame-add" className="text-[#e4c36a] underline">
            Open Frame Add
          </a>
          .
        </p>
      </header>

      <section className="rounded-3xl border border-[#e4c36a]/15 bg-[#111827]/75 p-6 shadow-2xl md:p-8">
        <h2 className="mb-6 text-2xl">Create News Story</h2>
        <CreateProjectForm />
      </section>

      {jobs.length ? (
        <section className="space-y-3">
          <h2 className="text-sm uppercase tracking-[0.18em] text-[#e4c36a]">Recent jobs</h2>
          <div className="grid gap-3">
            {jobs.map((job) => (
              <a
                key={job.id}
                href={`/jobs/${job.id}`}
                className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 hover:border-[#e4c36a]/40"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-xl">{job.title}</div>
                    <div className="text-sm text-white/50">
                      {job.location || "No location"} · {job.id}
                    </div>
                  </div>
                  <span className="text-sm text-[#e4c36a]">{job.status}</span>
                </div>
              </a>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
