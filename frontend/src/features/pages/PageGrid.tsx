import { pageImageUrl } from "../../services/api.ts";
import type { Page } from "../../types/index.ts";

interface Props {
  pages: Page[];
  onSelect: (pageId: number) => void;
}

export default function PageGrid({ pages, onSelect }: Props) {
  if (pages.length === 0) {
    return <p className="text-sm text-muted">No pages.</p>;
  }
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      {pages.map((page) => (
        <button
          key={page.id}
          onClick={() => onSelect(page.id)}
          className="overflow-hidden rounded-lg border border-line bg-surface text-left transition hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <img
            src={pageImageUrl(page.id, true)}
            alt={`Page ${page.page_index}`}
            loading="lazy"
            className="aspect-[2/3] w-full bg-raised object-cover"
          />
          <p className="flex items-center justify-between px-2 py-1.5 text-xs text-muted">
            <span>Page {page.page_index}</span>
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                page.analysis_status === "done" ? "bg-ok" : page.analysis_status === "failed" ? "bg-bad" : "bg-line"
              }`}
            />
          </p>
        </button>
      ))}
    </div>
  );
}
