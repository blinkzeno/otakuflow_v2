const BARS: Record<string, string> = {
  info: "bg-accent",
  success: "bg-ok",
  warn: "bg-warn",
  danger: "bg-bad",
  neutral: "bg-muted",
};

export default function ProgressBar({
  value,
  tone = "info",
}: {
  value: number;
  tone?: keyof typeof BARS;
}) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="h-2 overflow-hidden rounded bg-raised">
      <div className={`h-full ${BARS[tone]}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}
