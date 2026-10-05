import type { ReactNode } from "react";
import Icon, { type IconName } from "../ui/Icon.tsx";

export type StepStatus = "done" | "active" | "todo";

export interface Step {
  id: string;
  label: string;
  icon: IconName;
  status: StepStatus;
}

const DOTS: Record<StepStatus, string> = {
  done: "bg-ok",
  active: "bg-accent",
  todo: "bg-line",
};

export default function StepNav({
  steps,
  active,
  onGo,
}: {
  steps: Step[];
  active: string;
  onGo: (id: string) => void;
}) {
  return (
    <nav aria-label="Pipeline steps" className="space-y-1">
      {steps.map((step, pos) => (
        <button
          key={step.id}
          onClick={() => onGo(step.id)}
          aria-current={step.id === active ? "page" : undefined}
          className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
            step.id === active ? "bg-raised text-ink" : "text-muted hover:bg-raised/60 hover:text-ink"
          }`}
        >
          <span className="text-muted">{pos + 1}</span>
          <Icon name={step.icon} />
          <span className="flex-1">{step.label}</span>
          <span className={`h-2 w-2 rounded-full ${DOTS[step.status]}`} />
        </button>
      ))}
    </nav>
  );
}

export function StepNavRow({
  steps,
  active,
  onGo,
}: {
  steps: Step[];
  active: string;
  onGo: (id: string) => void;
}) {
  return (
    <nav
      aria-label="Pipeline steps"
      className="flex gap-1 overflow-x-auto border-b border-line pb-2"
    >
      {steps.map((step) => (
        <button
          key={step.id}
          onClick={() => onGo(step.id)}
          aria-current={step.id === active ? "page" : undefined}
          className={`flex shrink-0 items-center gap-2 rounded-md px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
            step.id === active ? "bg-raised text-ink" : "text-muted"
          }`}
        >
          <Icon name={step.icon} />
          {step.label}
          <span className={`h-2 w-2 rounded-full ${DOTS[step.status]}`} />
        </button>
      ))}
    </nav>
  );
}

export function SidebarShell({ children }: { children: ReactNode }) {
  return <div className="flex min-h-screen bg-base">{children}</div>;
}
