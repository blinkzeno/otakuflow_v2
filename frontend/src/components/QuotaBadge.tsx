import type { Quota, QuotaBucket } from "../types/index.ts";
import Badge from "./ui/Badge.tsx";
import type { Tone } from "./ui/Badge.tsx";

function Bucket({ bucket, label }: { bucket: QuotaBucket; label: string }) {
  const almostOut = bucket.cap > 0 && bucket.used / bucket.cap >= 0.9;
  const tone: Tone = almostOut ? "warn" : "neutral";
  return (
    <span title={bucket.model}>
      <Badge tone={tone}>
        {label} {bucket.used}/{bucket.cap}
      </Badge>
    </span>
  );
}

export default function QuotaBadge({ quota }: { quota: Quota | null }) {
  if (!quota) return null;
  return (
    <span className="flex gap-1">
      <Bucket bucket={quota.vision} label="Vision" />
      <Bucket bucket={quota.text} label="Text" />
    </span>
  );
}
