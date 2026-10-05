import type { Job } from "../types/index.ts";
import Badge, { type Tone } from "./ui/Badge.tsx";
import Button from "./ui/Button.tsx";
import Card from "./ui/Card.tsx";
import ProgressBar from "./ui/ProgressBar.tsx";

interface Props {
  job: Job;
  onCancel: () => void;
  onRetry: () => void;
}

const TONES: Record<string, Tone> = {
  queued: "neutral",
  running: "info",
  done: "success",
  failed: "danger",
  cancelled: "warn",
  paused: "warn",
};

const BARS: Record<string, "info" | "success" | "danger" | "neutral"> = {
  queued: "neutral",
  running: "info",
  done: "success",
  failed: "danger",
  cancelled: "neutral",
  paused: "neutral",
};

export default function JobProgress({ job, onCancel, onRetry }: Props) {
  const active = job.status === "running" || job.status === "queued";
  const retryable =
    job.status === "failed" ||
    job.status === "cancelled" ||
    job.status === "paused";
  return (
    <Card>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium capitalize">{job.stage}</span>
        <Badge tone={TONES[job.status] ?? "neutral"}>
          {job.status} ({job.progress}%)
        </Badge>
      </div>
      <div className="mt-2">
        <ProgressBar value={job.progress} tone={BARS[job.status] ?? "neutral"} />
      </div>
      {job.error && (
        <p className="mt-2 text-sm text-bad">{job.error}</p>
      )}
      <div className="mt-2 flex gap-3">
        {active && (
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        )}
        {retryable && (
          <Button variant="ghost" size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}
      </div>
    </Card>
  );
}
