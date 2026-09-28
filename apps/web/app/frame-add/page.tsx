import { FrameAddForm } from "@/components/FrameAddForm";
import { fetchFrameJobs } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FrameAddPage() {
  const jobs = await fetchFrameJobs().catch(() => []);

  return (
    <main className="space-y-10">
      <header className="space-y-3">
        <p className="text-sm uppercase tracking-[0.28em] text-[#e4c36a]">Broadcast chrome</p>
        <h1 className="text-4xl font-semibold leading-tight md:text-6xl">Frame Add</h1>
        <p className="max-w-2xl text-lg text-[#f6f1e8]/70">
          Pick 16:9 or 9:16, upload a video, and the software keys on the আমার কথা NEWS
          banner from your overlay clip. This does not touch the news reel editor.
        </p>
      </header>

      <section className="rounded-3xl border border-[#e4c36a]/15 bg-[#111827]/75 p-6 shadow-2xl md:p-8">
        <h2 className="mb-6 text-2xl">Add news frame</h2>
        <FrameAddForm />
      </section>

      {jobs.length ? (
        <section className="space-y-3">
          <h2 className="text-sm uppercase tracking-[0.18em] text-[#e4c36a]">Recent framed videos</h2>
          <div className="grid gap-3">
            {jobs.map((job) => (
              <a
                key={job.id}
                href={`/frame-add/${job.id}`}
                className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 hover:border-[#e4c36a]/40"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-xl">{job.header || job.footer || job.headline || job.location || "আমার কথা NEWS"}</div>
                    <div className="text-sm text-white/50">
                      {job.aspect_ratio} · {job.channel_name} · {job.id}
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
