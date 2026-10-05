import { useEffect, useState } from "react";
import {
  deleteSegment,
  exportScriptUrl,
  generateScript,
  listSegments,
  mergeSegment,
  patchSegment,
  reviewScript,
  splitSegment,
} from "../../services/api.ts";
import type { ScriptSegment } from "../../types/index.ts";
import Button from "../../components/ui/Button.tsx";
import EmptyState from "../../components/ui/EmptyState.tsx";
import SegmentCard from "./SegmentCard.tsx";

interface Props {
  chapterId: number;
  pageCount: number;
}

export default function ScriptEditor({ chapterId, pageCount }: Props) {
  const [segments, setSegments] = useState<ScriptSegment[] | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  async function reload(): Promise<void> {
    try {
      setSegments(await listSegments(chapterId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "load failed");
    }
  }

  useEffect(() => {
    setSegments(null);
    void reload();
  }, [chapterId]);

  async function run(action: () => Promise<unknown>): Promise<void> {
    setBusy(true);
    setError("");
    try {
      await action();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "action failed");
    } finally {
      setBusy(false);
    }
  }

  function onGenerate(confirm = false): void {
    void run(() => generateScript(chapterId, confirm));
  }

  function onReview(): void {
    if (!window.confirm("Lock the whole script as reviewed? Voice needs this.")) return;
    void run(() => reviewScript(chapterId));
  }

  if (segments === null && !error) {
    return <p className="text-sm text-muted">Loading script...</p>;
  }

  const drafts = (segments ?? []).filter((s) => s.status === "draft").length;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => onGenerate(false)} disabled={busy}>
          Generate
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            if (window.confirm("Replace EVERYTHING including reviewed?")) onGenerate(true);
          }}
          disabled={busy}
        >
          Regenerate all
        </Button>
        <Button
          variant="success"
          onClick={onReview}
          disabled={busy || (segments ?? []).length === 0}
        >
          Mark reviewed ({drafts} drafts)
        </Button>
        <a
          href={exportScriptUrl(chapterId)}
          className="rounded-md px-2 py-1 text-sm text-muted hover:text-ink hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          Export JSON
        </a>
      </div>
      {error && <p className="text-sm text-bad">{error}</p>}
      {(segments ?? []).length === 0 ? (
        <EmptyState
          title="No script yet"
          hint="Analyze pages first, then generate the narration."
          action={<Button size="sm" onClick={() => onGenerate(false)} disabled={busy}>Generate now</Button>}
        />
      ) : (
        segments!.map((seg, pos) => (
          <SegmentCard
            key={seg.id}
            seg={seg}
            pageCount={pageCount}
            isLast={pos === segments!.length - 1}
            onPatch={(key, body) => void run(() => patchSegment(key, body))}
            onSplit={(key) => void run(() => splitSegment(key))}
            onMerge={(key) => void run(() => mergeSegment(key))}
            onDelete={(key) => void run(() => deleteSegment(key))}
            onMove={(key, position) => void run(() => patchSegment(key, { position }))}
          />
        ))
      )}
    </div>
  );
}
