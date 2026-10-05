import { parseAnalysis } from "../../services/api.ts";
import type { Page } from "../../types/index.ts";
import Badge from "../../components/ui/Badge.tsx";
import Card from "../../components/ui/Card.tsx";
import EmptyState from "../../components/ui/EmptyState.tsx";

interface Props {
  page: Page;
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h4 className="font-medium text-muted">{title}</h4>
      <ul className="mt-1 list-disc pl-5 text-sm">
        {items.map((item, pos) => (
          <li key={pos}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function AnalysisPanel({ page }: Props) {
  if (page.analysis_status === "failed") {
    return (
      <Card>
        <p className="text-sm text-bad">
          Analysis failed{page.analysis_error ? `: ${page.analysis_error}` : ""}.
          Relaunch Analyze to retry this page.
        </p>
      </Card>
    );
  }
  const parsed = parseAnalysis(page);
  if (!parsed) {
    return <EmptyState title="Not analyzed yet" hint="Run Analyze to read this page." />;
  }
  return (
    <Card className="space-y-3 text-sm">
      <div className="flex items-center gap-2">
        <Badge tone="info">Importance {parsed.importance}/10</Badge>
        {parsed.location && (
          <span className="text-muted">{parsed.location}</span>
        )}
      </div>
      <p>{parsed.summary}</p>
      <Section title="Characters" items={parsed.characters} />
      <Section title="Actions" items={parsed.actions} />
      {parsed.dialogues.length > 0 && (
        <div>
          <h4 className="font-medium text-muted">Dialogues</h4>
          <ul className="mt-1 space-y-1">
            {parsed.dialogues.map((line, pos) => (
              <li key={pos} className="rounded-md bg-raised px-2 py-1">
                {line.speaker && (
                  <span className="font-medium">{line.speaker}: </span>
                )}
                {line.text}
              </li>
            ))}
          </ul>
        </div>
      )}
      <Section title="Events" items={parsed.events} />
      {parsed.visual_description && (
        <p className="text-xs text-muted">{parsed.visual_description}</p>
      )}
    </Card>
  );
}
