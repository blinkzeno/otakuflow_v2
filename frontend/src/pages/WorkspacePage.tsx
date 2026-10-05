import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  analyzeChapter,
  cancelJob,
  getLatestRender,
  getPage,
  getProject,
  getQuota,
  listPages,
  listSegments,
  renderChapter,
  retryImport,
  synthesizeChapter,
  synthesizeVoices,
} from "../services/api.ts";
import type {
  Job,
  Page,
  ProjectDetail,
  Quota,
  RenderInfo,
  ScriptSegment,
} from "../types/index.ts";
import JobProgress from "../components/JobProgress.tsx";
import AppShell from "../components/layout/AppShell.tsx";
import StepNav, { StepNavRow, type Step, type StepStatus } from "../components/layout/StepNav.tsx";
import Card from "../components/ui/Card.tsx";
import AnalysisPanel from "../features/analysis/AnalysisPanel.tsx";
import ExportPanel from "../features/export/ExportPanel.tsx";
import ScriptEditor from "../features/script/ScriptEditor.tsx";
import VoicePanel from "../features/voice/VoicePanel.tsx";
import PageDetail from "../features/pages/PageDetail.tsx";
import PageGrid from "../features/pages/PageGrid.tsx";
import { useJobsPolling } from "../hooks/useJobsPolling.ts";
import Button from "../components/ui/Button.tsx";
import EmptyState from "../components/ui/EmptyState.tsx";
import Skeleton from "../components/ui/Skeleton.tsx";
import { Field } from "../components/ui/Field.tsx";
import Badge from "../components/ui/Badge.tsx";

type Tab = "import" | "pages" | "analysis" | "script" | "voice" | "export";

const TABS: { id: Tab; label: string; icon: Step["icon"] }[] = [
  { id: "import", label: "Import", icon: "upload" },
  { id: "pages", label: "Pages", icon: "image" },
  { id: "analysis", label: "Analysis", icon: "chart" },
  { id: "script", label: "Script", icon: "script" },
  { id: "voice", label: "Voice", icon: "mic" },
  { id: "export", label: "Export", icon: "film" },
];

export default function WorkspacePage() {
  const { id } = useParams();
  const projectId = Number(id);
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [pages, setPages] = useState<Page[]>([]);
  const [segments, setSegments] = useState<ScriptSegment[]>([]);
  const [render, setRender] = useState<RenderInfo | null>(null);
  const [selected, setSelected] = useState<Page | null>(null);
  const [tab, setTab] = useState<Tab>("pages");
  const [error, setError] = useState<string>("");
  const [quota, setQuota] = useState<Quota | null>(null);
  const [analysisPageId, setAnalysisPageId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string>("");

  const { jobs } = useJobsPolling(
    Number.isFinite(projectId) ? projectId : null
  );
  const reloadedFor = useRef<string | null>(null);

  async function loadAll(project: number): Promise<void> {
    const loaded = await getProject(project);
    setDetail(loaded);
    const first = loaded.chapters[0];
    if (!first) {
      setPages([]);
      setSegments([]);
      setRender(null);
      return;
    }
    const [pageList, segList, latest] = await Promise.all([
      listPages(first.id),
      listSegments(first.id).catch(() => [] as ScriptSegment[]),
      getLatestRender(first.id).catch(() => null),
    ]);
    setPages(pageList);
    setSegments(segList);
    setRender(latest);
  }

  useEffect(() => {
    getQuota()
      .then(setQuota)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const done = jobs.find((job) => job.status === "done");
    const key = done ? `${done.stage}:${done.id}` : null;
    if (!done || !key || reloadedFor.current === key) return;
    reloadedFor.current = key;
    loadAll(projectId).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "load failed");
    });
    getQuota()
      .then(setQuota)
      .catch(() => undefined);
  }, [jobs, projectId]);

  useEffect(() => {
    if (!Number.isFinite(projectId)) {
      setError("Bad project link.");
      return;
    }
    loadAll(projectId).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "load failed");
    });
  }, [projectId]);

  async function onSelect(pageId: number): Promise<void> {
    try {
      setSelected(await getPage(pageId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }

  if (error) {
    return (
      <AppShell title="Otakuflow">
        <Card>
          <p className="text-sm text-bad">{error}</p>
          <Link to="/" className="mt-2 inline-block text-sm text-muted hover:text-ink hover:underline">
            Back to projects
          </Link>
        </Card>
      </AppShell>
    );
  }
  if (!detail) {
    return (
      <AppShell title="Otakuflow">
        <Skeleton lines={5} />
      </AppShell>
    );
  }

  const chapter = detail.chapters[0];
  const findJob = (stage: string): Job | undefined =>
    jobs.find((job) => job.stage === stage) ??
    detail.jobs.find((job) => job.stage === stage);
  const importJob = findJob("import");
  const analyzeJob = findJob("analyze");
  const voiceJob = findJob("tts");
  const renderJob = findJob("render");
  const analysisPage =
    pages.find((page) => page.id === analysisPageId) ?? pages[0] ?? null;

  const running = (stage: string): boolean => {
    const job = findJob(stage);
    return job?.status === "running" || job?.status === "queued";
  };

  function statusOf(step: Tab): StepStatus {
    if (!chapter) return "todo";
    switch (step) {
      case "import":
        return chapter.page_count > 0 ? "done" : running("import") ? "active" : "todo";
      case "pages":
        return pages.length > 0 ? "done" : "todo";
      case "analysis":
        return pages.some((p) => p.analysis_status === "done")
          ? "done"
          : running("analyze")
            ? "active"
            : "todo";
      case "script":
        if (segments.length === 0) return "todo";
        return segments.every((s) => s.status !== "draft") ? "done" : "active";
      case "voice":
        if (segments.length === 0) return "todo";
        return segments.every((s) => s.status === "voiced") ? "done" : "active";
      case "export":
        return render ? "done" : running("render") ? "active" : "todo";
    }
  }

  const steps: Step[] = TABS.map((t) => ({ ...t, status: statusOf(t.id) }));

  async function onCancelJob(jobId: number): Promise<void> {
    try {
      await cancelJob(jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "cancel failed");
    }
  }

  async function onCancelImport(): Promise<void> {
    if (!importJob) return;
    await onCancelJob(importJob.id);
  }

  async function onRetryImport(): Promise<void> {
    try {
      await retryImport(projectId);
      await loadAll(projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "retry failed");
    }
  }

  async function onAnalyze(): Promise<void> {
    if (!chapter) return;
    setNotice("");
    try {
      await analyzeChapter(chapter.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "analyze failed");
    }
  }

  async function onRetryVoice(): Promise<void> {
    if (!chapter) return;
    try {
      await synthesizeVoices(chapter.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "voice failed");
    }
  }

  async function onRetryRender(): Promise<void> {
    if (!chapter) return;
    try {
      await renderChapter(chapter.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "render failed");
    }
  }

  async function onSynthesize(): Promise<void> {
    if (!chapter) return;
    setNotice("");
    try {
      const result = await synthesizeChapter(chapter.id);
      await loadAll(projectId);
      setNotice(`Summary built from ${result.pages} pages.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "synthesis failed");
    }
  }

  return (
    <AppShell
      title={detail.project.title}
      quota={quota}
      sidebar={<StepNav steps={steps} active={tab} onGo={(stepId) => setTab(stepId as Tab)} />}
    >
      <div className="mb-4 lg:hidden">
        <StepNavRow steps={steps} active={tab} onGo={(stepId) => setTab(stepId as Tab)} />
      </div>

      {tab === "import" && (
        <section className="space-y-4">
          <Card>
            {!chapter ? (
              <p className="text-sm text-muted">No chapter yet.</p>
            ) : (
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <dt className="text-muted">Source file</dt>
                <dd className="truncate">{chapter.source_filename}</dd>
                <dt className="text-muted">Pages</dt>
                <dd>{chapter.page_count}</dd>
              </dl>
            )}
          </Card>
          {importJob && (
            <JobProgress
              job={importJob}
              onCancel={() => void onCancelImport()}
              onRetry={() => void onRetryImport()}
            />
          )}
        </section>
      )}

      {tab === "pages" && (
        <section>
          {selected && (
            <div className="mb-4">
              <PageDetail
                page={selected}
                total={pages.length}
                onClose={() => setSelected(null)}
              />
            </div>
          )}
          {pages.length === 0 ? (
            <EmptyState
              title="No pages yet"
              hint="Import a chapter first, pages appear here."
              action={<Button size="sm" variant="ghost" onClick={() => setTab("import")}>Go to Import</Button>}
            />
          ) : (
            <PageGrid pages={pages} onSelect={(pageId) => void onSelect(pageId)} />
          )}
        </section>
      )}

      {tab === "analysis" && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => void onAnalyze()}>Analyze</Button>
            <Button variant="ghost" onClick={() => void onSynthesize()}>
              Build chapter summary
            </Button>
            {notice && <Badge tone="success">{notice}</Badge>}
          </div>
          {analyzeJob && (
            <JobProgress
              job={analyzeJob}
              onCancel={() => void onCancelJob(analyzeJob.id)}
              onRetry={() => void onAnalyze()}
            />
          )}
          {chapter?.chapter_summary && (
            <Card>
              <details className="text-sm">
                <summary className="cursor-pointer font-medium">
                  Chapter summary
                </summary>
                <pre className="mt-2 overflow-auto text-xs text-muted">
                  {JSON.stringify(JSON.parse(chapter.chapter_summary), null, 2)}
                </pre>
              </details>
            </Card>
          )}
          {pages.length > 0 && (
            <Field label="Page">
              <select
                value={analysisPage?.id ?? ""}
                onChange={(e) => setAnalysisPageId(Number(e.target.value))}
                className="w-full rounded-md border border-line bg-raised px-3 py-1.5 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {pages.map((page) => (
                  <option key={page.id} value={page.id}>
                    Page {page.page_index} ({page.analysis_status})
                  </option>
                ))}
              </select>
            </Field>
          )}
          {analysisPage && <AnalysisPanel page={analysisPage} />}
        </section>
      )}

      {tab === "script" && (
        <section>
          {chapter ? (
            <ScriptEditor chapterId={chapter.id} pageCount={chapter.page_count} />
          ) : (
            <EmptyState title="No chapter yet" hint="Import a chapter first." />
          )}
        </section>
      )}

      {tab === "voice" && (
        <section className="space-y-4">
          {voiceJob && (
            <JobProgress
              job={voiceJob}
              onCancel={() => void onCancelJob(voiceJob.id)}
              onRetry={() => void onRetryVoice()}
            />
          )}
          {chapter ? (
            <VoicePanel chapterId={chapter.id} voiceJob={voiceJob} />
          ) : (
            <EmptyState title="No chapter yet" hint="Import a chapter first." />
          )}
        </section>
      )}

      {tab === "export" && (
        <section className="space-y-4">
          {renderJob && (
            <JobProgress
              job={renderJob}
              onCancel={() => void onCancelJob(renderJob.id)}
              onRetry={() => void onRetryRender()}
            />
          )}
          {chapter ? (
            <ExportPanel chapterId={chapter.id} renderJob={renderJob} />
          ) : (
            <EmptyState title="No chapter yet" hint="Import a chapter first." />
          )}
        </section>
      )}
    </AppShell>
  );
}
