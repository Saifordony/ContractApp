// A confidence value is never shown as a bare number. It is bucketed and colored
// so "low confidence — review manually" reads at a glance, satisfying the
// no-tooltip-needed bar from the brief.

export function confidenceBucket(value: number): "high" | "medium" | "low" {
  if (value >= 0.66) return "high";
  if (value >= 0.4) return "medium";
  return "low";
}

export function ConfidenceBadge({ value }: { value: number }) {
  const bucket = confidenceBucket(value);
  const label =
    bucket === "high"
      ? "High confidence"
      : bucket === "medium"
        ? "Medium confidence"
        : "Low confidence — verify";
  const pct = Math.round(value * 100);
  return (
    <span className={`badge ${bucket}`} title={`${pct}% confidence`}>
      {label} · {pct}%
    </span>
  );
}
