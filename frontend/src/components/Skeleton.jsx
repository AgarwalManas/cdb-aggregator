// A single shimmering placeholder block. Compose these into loading layouts that
// mirror the shape of the content they stand in for.
export default function Skeleton({ width = "100%", height = 16, radius = 6, className = "" }) {
  return (
    <span
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius: radius }}
      aria-hidden="true"
    />
  );
}

// A card of stacked lines — the default loading shape for a panel or list.
export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="card skeleton-card" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} width={i === 0 ? "40%" : `${88 - i * 12}%`} />
      ))}
    </div>
  );
}
