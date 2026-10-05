import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import QuotaBadge from "../QuotaBadge.tsx";
import type { Quota } from "../../types/index.ts";
import Icon from "../ui/Icon.tsx";

export default function AppShell({
  sidebar,
  title,
  quota,
  children,
}: {
  sidebar?: ReactNode;
  title: string;
  quota?: Quota | null;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-base text-ink">
      {sidebar && (
        <aside className="hidden w-[260px] shrink-0 flex-col gap-6 border-r border-line bg-surface p-4 lg:flex">
          <Link to="/" className="flex items-center gap-2 px-1 text-base font-bold">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-accent-ink">
              <Icon name="play" />
            </span>
            Otakuflow
          </Link>
          <div className="flex-1">{sidebar}</div>
          <div className="border-t border-line pt-3">
            <QuotaBadge quota={quota ?? null} />
          </div>
        </aside>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-line bg-surface px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              to="/"
              className="rounded-md p-1.5 text-muted hover:bg-raised hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent lg:hidden"
              aria-label="Back to projects"
            >
              <Icon name="back" />
            </Link>
            <h1 className="truncate text-lg font-bold">{title}</h1>
          </div>
          <div className="lg:hidden">
            <QuotaBadge quota={quota ?? null} />
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
          {children}
        </main>
      </div>
    </div>
  );
}
