// Single place for HTTP calls. No secret ever lives here.

import type {
  Job,
  Page,
  PageAnalysis,
  Project,
  ProjectDetail,
  Quota,
  RenderInfo,
  ScriptSegment,
  Timeline,
} from "../types/index.ts";

export const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

export interface Health {
  status: string;
}

async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `request failed: ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // keep default message
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE}/api/health`);
  return readJson<Health>(res);
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE}/api/projects`);
  return readJson<Project[]>(res);
}

export interface CreateResult {
  project_id: number;
  job_id: number;
}

export async function createProject(
  file: File,
  title: string
): Promise<CreateResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);
  const res = await fetch(`${API_BASE}/api/projects`, {
    method: "POST",
    body: form,
  });
  return readJson<CreateResult>(res);
}

export async function getProject(id: number): Promise<ProjectDetail> {
  const res = await fetch(`${API_BASE}/api/projects/${id}`);
  return readJson<ProjectDetail>(res);
}

export async function deleteProject(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/projects/${id}`, {
    method: "DELETE",
  });
  await readJson<{ deleted: number }>(res);
}

export async function listPages(chapterId: number): Promise<Page[]> {
  const res = await fetch(`${API_BASE}/api/chapters/${chapterId}/pages`);
  return readJson<Page[]>(res);
}

export async function getPage(id: number): Promise<Page> {
  const res = await fetch(`${API_BASE}/api/pages/${id}`);
  return readJson<Page>(res);
}

export function pageImageUrl(id: number, thumb = false): string {
  return `${API_BASE}/api/pages/${id}/image${thumb ? "?thumb=true" : ""}`;
}

export async function listJobs(projectId: number): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/jobs`);
  return readJson<Job[]>(res);
}

export async function cancelJob(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/jobs/${id}/cancel`, {
    method: "POST",
  });
  await readJson<{ status: string }>(res);
}

export async function retryImport(projectId: number): Promise<{
  project_id: number;
  job_id: number;
}> {
  const res = await fetch(
    `${API_BASE}/api/projects/${projectId}/retry-import`,
    { method: "POST" }
  );
  return readJson<{ project_id: number; job_id: number }>(res);
}

export async function analyzeChapter(chapterId: number): Promise<{
  chapter_id: number;
  job_id: number;
}> {
  const res = await fetch(`${API_BASE}/api/chapters/${chapterId}/analyze`, {
    method: "POST",
  });
  return readJson<{ chapter_id: number; job_id: number }>(res);
}

export async function synthesizeChapter(chapterId: number): Promise<{
  pages: number;
}> {
  const res = await fetch(
    `${API_BASE}/api/chapters/${chapterId}/synthesize`,
    { method: "POST" }
  );
  return readJson<{ pages: number }>(res);
}

export async function getQuota(): Promise<Quota> {
  const res = await fetch(`${API_BASE}/api/quota`);
  return readJson<Quota>(res);
}

export function parseAnalysis(page: Page): PageAnalysis | null {
  if (!page.analysis_json) return null;
  try {
    return JSON.parse(page.analysis_json) as PageAnalysis;
  } catch {
    return null;
  }
}

function withRefs(segment: ScriptSegment): ScriptSegment {
  const raw = segment.page_refs as unknown;
  let refs: number[] = [];
  if (typeof raw === "string") {
    try {
      const parsed: unknown = JSON.parse(raw);
      if (Array.isArray(parsed)) refs = parsed.filter((i) => typeof i === "number");
    } catch {
      refs = [];
    }
  } else if (Array.isArray(raw)) {
    refs = raw.filter((i) => typeof i === "number");
  }
  return { ...segment, page_refs: refs };
}

export async function generateScript(
  chapterId: number,
  confirmOverwrite = false
): Promise<{ segments: number }> {
  const res = await fetch(`${API_BASE}/api/chapters/${chapterId}/script`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      confirmOverwrite ? { confirm_overwrite: true } : {}
    ),
  });
  return readJson<{ segments: number }>(res);
}

export async function listSegments(chapterId: number): Promise<ScriptSegment[]> {
  const res = await fetch(`${API_BASE}/api/chapters/${chapterId}/script`);
  const rows = await readJson<ScriptSegment[]>(res);
  return rows.map(withRefs);
}

export async function patchSegment(
  key: string,
  body: { text?: string; page_refs?: number[]; position?: number }
): Promise<ScriptSegment> {
  const res = await fetch(`${API_BASE}/api/segments/${key}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return withRefs(await readJson<ScriptSegment>(res));
}

export async function splitSegment(key: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/segments/${key}/split`, {
    method: "POST",
  });
  await readJson<{ split: string }>(res);
}

export async function mergeSegment(key: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/segments/${key}/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ with_next: true }),
  });
  await readJson<{ merged: string }>(res);
}

export async function deleteSegment(key: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/segments/${key}`, {
    method: "DELETE",
  });
  await readJson<{ deleted: string }>(res);
}

export async function reviewScript(chapterId: number): Promise<{
  reviewed: number;
}> {
  const res = await fetch(
    `${API_BASE}/api/chapters/${chapterId}/script/review`,
    { method: "POST" }
  );
  return readJson<{ reviewed: number }>(res);
}

export function exportScriptUrl(chapterId: number): string {
  return `${API_BASE}/api/chapters/${chapterId}/script/export`;
}

export async function synthesizeVoices(chapterId: number): Promise<{
  chapter_id: number;
  job_id: number;
}> {
  const res = await fetch(`${API_BASE}/api/chapters/${chapterId}/voice`, {
    method: "POST",
  });
  return readJson<{ chapter_id: number; job_id: number }>(res);
}

export async function regenerateVoice(key: string): Promise<{
  duration: number;
}> {
  const res = await fetch(`${API_BASE}/api/segments/${key}/voice`, {
    method: "POST",
  });
  return readJson<{ duration: number }>(res);
}

export function audioUrl(key: string): string {
  return `${API_BASE}/api/segments/${key}/audio`;
}

export async function renderChapter(
  chapterId: number,
  settings?: Record<string, unknown>
): Promise<{
  chapter_id: number;
  job_id: number;
}> {
  const res = await fetch(`${API_BASE}/api/chapters/${chapterId}/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings ? { settings } : {}),
  });
  return readJson<{ chapter_id: number; job_id: number }>(res);
}

export async function getTimeline(chapterId: number): Promise<Timeline> {
  const res = await fetch(`${API_BASE}/api/chapters/${chapterId}/timeline`);
  return readJson<Timeline>(res);
}

export async function getLatestRender(
  chapterId: number
): Promise<RenderInfo | null> {
  const res = await fetch(
    `${API_BASE}/api/chapters/${chapterId}/render/latest`
  );
  if (res.status === 404) return null;
  return readJson<RenderInfo>(res);
}

export function videoUrl(renderId: number): string {
  return `${API_BASE}/api/renders/${renderId}/video`;
}
