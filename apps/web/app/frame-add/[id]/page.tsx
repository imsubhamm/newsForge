import Link from "next/link";

import { FrameJobDetail } from "@/components/FrameJobDetail";
import { fetchFrameJob } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function FrameJobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let job;
  try {
    job = await fetchFrameJob(id);
  } catch {
    return (
      <main className="space-y-4">
        <h1 className="text-3xl">Frame job not found</h1>
        <Link href="/frame-add" className="text-[#e4c36a] underline">
          Back to Frame Add
        </Link>
      </main>
    );
  }

  return (
    <main className="space-y-8">
      <Link href="/frame-add" className="text-sm text-[#e4c36a]">
        ← Frame Add
      </Link>
      <header>
        <p className="text-sm uppercase tracking-[0.18em] text-[#e4c36a]">Framed video</p>
        <h1 className="mt-2 text-4xl">{job.header || job.footer || job.headline || "বিশেষ সংবাদ"}</h1>
        <p className="mt-2 text-white/60">
          {job.aspect_ratio} · {job.channel_name} · {job.id}
        </p>
      </header>
      <FrameJobDetail initial={job} />
    </main>
  );
}
