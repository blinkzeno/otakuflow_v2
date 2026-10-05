import { useEffect, useState } from "react";
import {
  audioUrl,
  listSegments,
  regenerateVoice,
  synthesizeVoices,
} from "../../services/api.ts";
import type { Job, ScriptSegment } from "../../types/index.ts";
import Badge from "../../components/ui/Badge.tsx";
import Button from "../../components/ui/Button.tsx";
import Card from "../../components/ui/Card.tsx";
import EmptyState from "../../components/ui/EmptyState.tsx";

interface Props {
  chapterId: number;
  voiceJob: Job | undefined;
}

export default function VoicePanel({ chapterId, voiceJob }: Props) {
  const [segments, setSegments] = useState<ScriptSegment[] | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [durations, setDurations] = useState<Record<string, number>>({});

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

  useEffect(() => {
    if (voiceJob && voiceJob.status === "done") void reload();
  }, [voiceJob?.status]);

  async function onGenerate(): Promise<void> {
    setBusy(true);
    setError("");
    try {
      await synthesizeVoices(chapterId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "voice failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRegenerate(key: string): Promise<void> {
    setError("");
    try {
      const result = await regenerateVoice(key);
      setDurations((prev) => ({ ...prev, [key]: result.duration }));
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "regen failed");
    }
  }

  function onMetadata(key: string, seconds: number): void {
    setDurations((prev) =>
      prev[key] !== undefined ? prev : { ...prev, [key]: seconds }
    );
  }

  if (segments === null && !error) {
    return <p className="text-sm text-muted">Loading voices...</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Button onClick={() => void onGenerate()} disabled={busy}>
          Generate voice
        </Button>
        <span className="text-sm text-muted">
          Only reviewed segments with changed text are synthesized.
        </span>
      </div>
      {error && <p className="text-sm text-bad">{error}</p>}
      {(segments ?? []).length === 0 ? (
        <EmptyState
          title="No script yet"
          hint="Generate and review the script first, then come back for voice."
        />
      ) : (
        (segments ?? []).map((seg) => (
          <Card key={seg.id}>
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">#{seg.position}</span>
              <span className="flex items-center gap-2">
                <Badge tone={seg.status === "voiced" ? "success" : "neutral"}>
                  {seg.status}
                </Badge>
                {durations[seg.segment_key] !== undefined && (
                  <span className="text-xs text-muted">
                    {durations[seg.segment_key].toFixed(1)}s
                  </span>
                )}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">{seg.text}</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              {seg.status === "voiced" && (
                <audio
                  controls
                  preload="none"
                  src={audioUrl(seg.segment_key)}
                  onLoadedMetadata={(e) =>
                    onMetadata(seg.segment_key, e.currentTarget.duration)
                  }
                  className="w-full sm:w-auto"
                />
              )}
              <Button variant="ghost" size="sm" onClick={() => void onRegenerate(seg.segment_key)}>
                Regenerate
              </Button>
            </div>
          </Card>
        ))
      )}
    </div>
  );
}
