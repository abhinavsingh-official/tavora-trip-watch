import { formatInr } from '../format';
import type { PriceObservation } from '../types';

const DEFAULT_MAX_POINTS = 12;

// Only the most recent window, or an old price spike dominates the chart instead of showing a readable recent trend
export default function PriceHistoryChart({
  observations,
  budget,
  maxPoints = DEFAULT_MAX_POINTS,
}: {
  observations: PriceObservation[];
  budget: number;
  maxPoints?: number;
}) {
  const valid = observations
    .filter((o) => o.status === 'complete' && o.total_price !== null)
    .slice()
    .sort((a, b) => new Date(a.observed_at).getTime() - new Date(b.observed_at).getTime())
    .slice(-maxPoints);

  if (valid.length < 2) {
    return <p className="muted">Need at least 2 complete checks to show a history chart.</p>;
  }

  const width = 480;
  const height = 150;
  const padLeft = 64;
  const padRight = 12;
  const padTop = 12;
  const padBottom = 24;
  const totals = valid.map((o) => o.total_price as number);
  const minY = Math.min(...totals, budget);
  const maxY = Math.max(...totals, budget);
  const spanY = maxY - minY || 1;

  const x = (i: number) => padLeft + (i / (valid.length - 1)) * (width - padLeft - padRight);
  const y = (v: number) =>
    height - padBottom - ((v - minY) / spanY) * (height - padTop - padBottom);

  const linePoints = totals.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const budgetY = y(budget);

  const yTickCount = 4;
  const yTicks = Array.from({ length: yTickCount + 1 }, (_, i) => minY + (spanY * i) / yTickCount);

  const firstDate = new Date(valid[0].observed_at);
  const lastDate = new Date(valid[valid.length - 1].observed_at);
  const shortDate = (d: Date) => d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="price-history-chart"
      role="img"
      aria-label="Price history chart"
    >
      {yTicks.map((v, i) => (
        <g key={i}>
          <line x1={padLeft} y1={y(v)} x2={width - padRight} y2={y(v)} stroke="var(--color-border)" strokeWidth={1} />
          <text x={padLeft - 8} y={y(v)} textAnchor="end" dominantBaseline="middle" className="chart-axis-label">
            ₹{formatInr(v)}
          </text>
        </g>
      ))}
      <line
        x1={padLeft}
        y1={budgetY}
        x2={width - padRight}
        y2={budgetY}
        stroke="var(--color-text-muted)"
        strokeDasharray="4 3"
        strokeWidth={1}
      />
      <text x={width - padRight} y={budgetY - 4} textAnchor="end" className="chart-axis-label">
        Budget ₹{formatInr(budget)}
      </text>
      <polyline fill="none" stroke="var(--color-accent)" strokeWidth={2} points={linePoints} />
      {totals.map((v, i) => (
        <circle key={i} cx={x(i)} cy={y(v)} r={3} fill="var(--color-accent)" />
      ))}
      <text x={padLeft} y={height - 6} textAnchor="start" className="chart-axis-label">
        {shortDate(firstDate)}
      </text>
      <text x={width - padRight} y={height - 6} textAnchor="end" className="chart-axis-label">
        {shortDate(lastDate)}
      </text>
    </svg>
  );
}
