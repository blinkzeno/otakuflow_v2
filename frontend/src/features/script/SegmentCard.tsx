import { useState } from "react";
import type { ScriptSegment } from "../../types/index.ts";
import Badge from "../../components/ui/Badge.tsx";
import Button from "../../components/ui/Button.tsx";
import Card from "../../components/ui/Card.tsx";
import { TextArea } from "../../components/ui/Field.tsx";
import Icon from "../../components/ui/Icon.tsx";

interface Props {
  seg: ScriptSegment;
  pageCount: number;
  isLast: boolean;
  onPatch: (key: string, body: { text?: string; page_refs?: number[]; position?: number }) => void;
  onSplit: (key: string) => void;
  onMerge: (key: string) => void;
  onDelete: (key: string) => void;
  onMove: (key: string, position: number) => void;
}

export default function SegmentCard({
  seg,
  pageCount,
  isLast,
  onPatch,
  onSplit,
  onMerge,
  onDelete,
  onMove,
}: Props) {
  const [draft, setDraft] = useState<string | null>(null);
  const [newRef, setNewRef] = useState<string>("");

  function saveText(): void {
    if (draft !== null && draft !== seg.text) onPatch(seg.segment_key, { text: draft });
    setDraft(null);
  }

  function addRef(): void {
    const index = Number(newRef);
    if (!Number.isInteger(index) || index < 1 || index > pageCount) return;
    if (seg.page_refs.includes(index)) {
      setNewRef("");
      return;
    }
    onPatch(seg.segment_key, { page_refs: [...seg.page_refs, index] });
    setNewRef("");
  }

  function removeRef(index: number): void {
    onPatch(
      seg.segment_key,
      { page_refs: seg.page_refs.filter((i) => i !== index) }
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">#{seg.position}</span>
        <span className="flex items-center gap-2 text-muted">
          <Badge tone={seg.status === "voiced" ? "success" : seg.status === "reviewed" ? "info" : "neutral"}>
            {seg.status}
          </Badge>
          <span className="text-xs">
            ~{seg.duration_estimate ?? 0}s · p{seg.page_refs.join(", p") || "—"}
          </span>
        </span>
      </div>
      <TextArea
        value={draft ?? seg.text}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={saveText}
        rows={3}
        className="mt-2"
      />
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {seg.page_refs.map((index) => (
          <span
            key={index}
            className="flex items-center gap-1 rounded-md bg-raised px-2 py-0.5 text-xs"
          >
            p{index}
            <button
              onClick={() => removeRef(index)}
              className="text-muted hover:text-bad focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              title="Remove page"
              aria-label={`Remove page ${index}`}
            >
              <Icon name="x" />
            </button>
          </span>
        ))}
        <input
          value={newRef}
          onChange={(e) => setNewRef(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") addRef();
          }}
          placeholder={`+ page 1-${pageCount}`}
          aria-label="Add page reference"
          className="w-28 rounded-md border border-line bg-raised px-2 py-0.5 text-xs text-ink placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <Button variant="ghost" size="sm" onClick={() => onMove(seg.segment_key, seg.position - 1)} aria-label="Move up">↑</Button>
        <Button variant="ghost" size="sm" onClick={() => onMove(seg.segment_key, seg.position + 1)} aria-label="Move down">↓</Button>
        <Button variant="ghost" size="sm" onClick={() => onSplit(seg.segment_key)}>Split</Button>
        {!isLast && (
          <Button variant="ghost" size="sm" onClick={() => onMerge(seg.segment_key)}>Merge ↓</Button>
        )}
        <Button
          variant="danger"
          size="sm"
          onClick={() => {
            if (window.confirm("Delete this segment?")) onDelete(seg.segment_key);
          }}
        >
          Delete
        </Button>
      </div>
    </Card>
  );
}
