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
  // The chart's job is to show how the price itself is moving - scale the axis off the price
  // values only. The budget is usually far above the actual prices (that's the whole point of a
  // below-budget alert), so letting it dictate the scale used to squeeze every real fluctuation
  // into a sliver at the bottom of the chart, making it look flat even when the price was moving.
  const totals = valid.map((o) => o.total_price as number);
  const minTotal = Math.min(...totals);
  const maxTotal = Math.max(...totals);
  const totalSpan = maxTotal - minTotal;
  // A little breathing room even when the price barely moved, so points never sit flush on an edge
  const pad = Math.max(totalSpan * 0.2, maxTotal * 0.02, 25);
  const minY = minTotal - pad;
  const maxY = maxTotal + pad;
  const spanY = maxY - minY || 1;

  const x = (i: number) => padLeft + (i / (valid.length - 1)) * (width - padLeft - padRight);
  const y = (v: number) =>
    height - padBottom - ((v - minY) / spanY) * (height - padTop - padBottom);

  const linePoints = totals.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const budgetInRange = budget >= minY && budget <= maxY;
  const budgetY = budgetInRange ? y(budget) : null;

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
      {budgetY !== null ? (
        <>
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
        </>
      ) : (
        // Budget sits well outside the price range shown here - say so instead of stretching the
        // scale to fit it in, which would flatten every real price movement into a thin band.
        <text x={width - padRight} y={padTop + 8} textAnchor="end" className="chart-axis-label">
          Budget ₹{formatInr(budget)} ({budget > maxY ? 'well above' : 'well below'} this range)
        </text>
      )}
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
