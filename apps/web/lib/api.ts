import type { AudioMode, FrameJob, Job, SemanticDebug, TimelinePlan } from "./types";

export function apiOrigin(): string {
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    return `${protocol}//${window.location.hostname}:8000`;
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
}

export function apiUrl(path: string): string {
  if (typeof window === "undefined") {
    return `${apiOrigin()}${path}`;
  }
  return path;
}

export function mediaUrl(path: string | null | undefined): string {
  if (!path) {
    return "";
  }
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${apiOrigin()}${path.startsWith("/") ? path : `/${path}`}`;
}

function apiErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }
  const detail = (payload as { detail?: unknown; error?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => (typeof item === "string" ? item : item?.msg || JSON.stringify(item)))
      .join(" ");
  }
  const error = (payload as { error?: unknown }).error;
  if (typeof error === "string" && error.trim()) {
    return error;
  }
  return fallback;
}

export async function createJob(form: FormData, onProgress: (pct: number) => void): Promise<Job> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    // Post straight to FastAPI so large WhatsApp clips are not truncated by the Next.js 10MB proxy buffer.
    xhr.open("POST", `${apiOrigin()}/api/jobs`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed. Is the API running on port 8000?"));
    xhr.onload = () => {
      const raw = xhr.responseText?.trim() ?? "";
      if (!raw) {
        reject(
          new Error(
            xhr.status >= 400
              ? `Upload failed (HTTP ${xhr.status}). The files may be too large for the current proxy.`
              : "The server returned an empty response.",
          ),
        );
        return;
      }
      try {
        const payload = JSON.parse(raw);
        if (xhr.status >= 400) {
          reject(new Error(apiErrorMessage(payload, "Could not create the project")));
          return;
        }
        resolve(payload as Job);
      } catch {
        reject(
          new Error(
            "The server could not accept this upload. Check that the API is running and that the clips are MP4/MOV.",
          ),
        );
      }
    };
    xhr.send(form);
  });
}

export async function fetchJob(id: string): Promise<Job> {
  const response = await fetch(apiUrl(`/api/jobs/${id}`), { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Job not found");
  }
  return response.json();
}

export async function startJobProcess(id: string): Promise<Job> {
  const response = await fetch(apiUrl(`/api/jobs/${id}/process`), { method: "POST" });
  if (!response.ok) {
    throw new Error("Could not start processing");
  }
  return response.json();
}

export async function fetchSemanticDebug(id: string): Promise<SemanticDebug | null> {
  const response = await fetch(apiUrl(`/api/jobs/${id}/semantic-debug`), { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export async function fetchTimeline(id: string): Promise<TimelinePlan | null> {
  const response = await fetch(apiUrl(`/api/jobs/${id}/timeline`), { cache: "no-store" });
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export async function setClipAudioMode(id: string, clipIndex: number, mode: AudioMode): Promise<TimelinePlan> {
  const response = await fetch(apiUrl(`/api/jobs/${id}/audio-mode`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clip_index: clipIndex, mode }),
  });
  if (!response.ok) {
    throw new Error("Could not update the audio block");
  }
  return response.json();
}

export async function renderExistingJob(id: string): Promise<Job> {
  const response = await fetch(apiUrl(`/api/jobs/${id}/render`), { method: "POST" });
  if (!response.ok) {
    throw new Error("Could not start render");
  }
  return response.json();
}

export async function fetchJobs(): Promise<Job[]> {
  const response = await fetch(apiUrl("/api/jobs"), { cache: "no-store" });
  if (!response.ok) {
    return [];
  }
  const payload = await response.json();
  return payload.jobs ?? [];
}

export async function createFrameJob(form: FormData, onProgress: (pct: number) => void): Promise<FrameJob> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${apiOrigin()}/api/frames`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed. Is the API running on port 8000?"));
    xhr.onload = () => {
      const raw = xhr.responseText?.trim() ?? "";
      if (!raw) {
        reject(new Error("The server returned an empty response."));
        return;
      }
      try {
        const payload = JSON.parse(raw);
        if (xhr.status >= 400) {
          reject(new Error(apiErrorMessage(payload, "Could not add the frame")));
          return;
        }
        resolve(payload as FrameJob);
      } catch {
        reject(new Error("The server could not accept this video. Check that the API is running."));
      }
    };
    xhr.send(form);
  });
}

export async function fetchFrameJob(id: string): Promise<FrameJob> {
  const response = await fetch(apiUrl(`/api/frames/${id}`), { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Frame job not found");
  }
  return response.json();
}

export async function fetchFrameJobs(): Promise<FrameJob[]> {
  const response = await fetch(apiUrl("/api/frames"), { cache: "no-store" });
  if (!response.ok) {
    return [];
  }
  const payload = await response.json();
  return payload.jobs ?? [];
}
