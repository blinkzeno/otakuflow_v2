export default function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-2 rounded-lg border border-line bg-surface p-4">
      {Array.from({ length: lines }).map((_, pos) => (
        <div key={pos} className="h-4 rounded bg-raised" />
      ))}
    </div>
  );
}
