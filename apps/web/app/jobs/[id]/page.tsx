import Link from "next/link";

import { JobDetail } from "@/components/JobDetail";
import { fetchJob } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let job;
  try {
    job = await fetchJob(id);
  } catch {
    return (
      <main className="space-y-4">
        <h1 className="text-3xl">Job not found</h1>
        <Link href="/" className="text-[#e4c36a] underline">
          Back to dashboard
        </Link>
      </main>
    );
  }

  return (
    <main className="space-y-8">
      <Link href="/" className="text-sm text-[#e4c36a]">
        ← Dashboard
      </Link>
      <header>
        <p className="text-sm uppercase tracking-[0.18em] text-[#e4c36a]">News project</p>
        <h1 className="mt-2 text-4xl">{job.title}</h1>
        <p className="mt-2 text-white/60">
          {job.location || "Location pending"} · Reporter {job.reporter_name || "—"} · {job.id}
        </p>
      </header>
      <JobDetail initial={job} />
    </main>
  );
}
