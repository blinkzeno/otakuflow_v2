import { useEffect, useState } from "react";
import {
  getLatestRender,
  getTimeline,
  pageImageUrl,
  renderChapter,
  videoUrl,
} from "../../services/api.ts";
import type { Job, RenderInfo, Timeline } from "../../types/index.ts";
import Button from "../../components/ui/Button.tsx";
import Card from "../../components/ui/Card.tsx";
import EmptyState from "../../components/ui/EmptyState.tsx";

interface Props {
  chapterId: number;
  renderJob: Job | undefined;
}

function formatTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = (seconds % 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${rest}`;
}

export default function ExportPanel({ chapterId, renderJob }: Props) {
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [render, setRender] = useState<RenderInfo | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  async function reload(): Promise<void> {
    try {
      setTimeline(await getTimeline(chapterId));
      setError("");
    } catch (err) {
      setTimeline(null);
      setError(err instanceof Error ? err.message : "timeline failed");
      return;
    }
    try {
      setRender(await getLatestRender(chapterId));
    } catch {
      setRender(null);
    }
  }

  useEffect(() => {
    void reload();
  }, [chapterId]);

  useEffect(() => {
    if (renderJob && renderJob.status === "done") void reload();
  }, [renderJob?.status]);

  async function onRender(): Promise<void> {
    setBusy(true);
    setError("");
    try {
      await renderChapter(chapterId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "render failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => void onRender()} disabled={busy}>
          Render MP4
        </Button>
        {timeline && (
          <span className="text-sm text-muted">
            {timeline.clips.length} clips · {formatTime(timeline.total)}
          </span>
        )}
      </div>
      {error && (
        <EmptyState
          title="No timeline yet"
          hint={error}
          action={<Button size="sm" onClick={() => void reload()}>Retry</Button>}
        />
      )}
      {timeline && (
        <div className="flex flex-wrap gap-2">
          {timeline.clips.slice(0, 12).map((clip) => {
            const first = clip.pages[0];
            if (!first) return null;
            const focus = first.focus;
            return (
              <div
                key={clip.segment_key}
                className="relative w-20 overflow-hidden rounded-md border border-line bg-raised"
                title={`Focus on page ${first.index}`}
              >
                <img
                  src={pageImageUrl(first.id, true)}
                  alt={`Page ${first.index}`}
                  loading="lazy"
                  className="aspect-[2/3] w-full object-cover"
                />
                {focus && (
                  <span
                    className="absolute border-2 border-ok"
                    style={{
                      left: `${focus.x / 10}%`,
                      top: `${focus.y / 10}%`,
                      width: `${focus.w / 10}%`,
                      height: `${focus.h / 10}%`,
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
      {timeline && (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[520px] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-muted">
                <th className="px-3 py-2 font-medium">#</th>
                <th className="px-3 py-2 font-medium">Segment</th>
                <th className="px-3 py-2 font-medium">Start</th>
                <th className="px-3 py-2 font-medium">Duration</th>
                <th className="px-3 py-2 font-medium">Pages</th>
              </tr>
            </thead>
            <tbody>
              {timeline.clips.map((clip) => (
                <tr key={clip.segment_key} className="border-b border-line/50 last:border-0">
                  <td className="px-3 py-1.5">{clip.position}</td>
                  <td className="px-3 py-1.5 font-mono text-xs text-muted">{clip.segment_key}</td>
                  <td className="px-3 py-1.5">{formatTime(clip.start)}</td>
                  <td className="px-3 py-1.5">{clip.duration.toFixed(1)}s</td>
                  <td className="px-3 py-1.5">
                    {clip.pages.map((p) => p.index).join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {render?.video_rel_path && (
        <Card className="space-y-2">
          <video controls src={videoUrl(render.id)} className="max-h-[60vh] w-full rounded-md border border-line bg-black" />
          <div>
            <a
              href={videoUrl(render.id)}
              download
              className="text-sm text-muted hover:text-ink hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              Download MP4
            </a>
          </div>
        </Card>
      )}
    </div>
  );
}
