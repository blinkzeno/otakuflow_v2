import type { ReactNode } from "react";

export type Tone = "info" | "success" | "warn" | "danger" | "neutral";

const TONES: Record<Tone, string> = {
  info: "bg-accent/15 text-accent",
  success: "bg-ok/15 text-ok",
  warn: "bg-warn/15 text-warn",
  danger: "bg-bad/15 text-bad",
  neutral: "bg-raised text-muted",
};

export default function Badge({
  tone = "neutral",
  children,
}: {
  tone?: Tone;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}
