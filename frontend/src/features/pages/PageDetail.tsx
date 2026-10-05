import { pageImageUrl } from "../../services/api.ts";
import type { Page } from "../../types/index.ts";
import Badge from "../../components/ui/Badge.tsx";
import Button from "../../components/ui/Button.tsx";
import Card from "../../components/ui/Card.tsx";

interface Props {
  page: Page;
  total: number;
  onClose: () => void;
}

export default function PageDetail({ page, total, onClose }: Props) {
  return (
    <Card className="flex flex-col gap-4 md:flex-row">
      <img
        src={pageImageUrl(page.id)}
        alt={`Page ${page.page_index}`}
        className="max-h-[60vh] rounded-md border border-line bg-raised object-contain"
      />
      <div className="text-sm">
        <div className="flex items-center justify-between gap-6">
          <h3 className="font-semibold">
            Page {page.page_index} of {total}
          </h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
        <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1">
          <dt className="text-muted">File</dt>
          <dd className="truncate">{page.filename}</dd>
          <dt className="text-muted">Size</dt>
          <dd>
            {page.width} x {page.height}
          </dd>
          <dt className="text-muted">Analysis</dt>
          <dd>
            <Badge
              tone={
                page.analysis_status === "done"
                  ? "success"
                  : page.analysis_status === "failed"
                    ? "danger"
                    : "neutral"
              }
            >
              {page.analysis_status}
            </Badge>
          </dd>
        </dl>
      </div>
    </Card>
  );
}
