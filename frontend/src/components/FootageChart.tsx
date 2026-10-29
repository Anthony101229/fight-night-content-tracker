import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { capitalize, formatDate } from "../format";
import { usePalette } from "../palette";
import type { FootageStatus, FootageSummary } from "../types";

// Stack order: delivered sits on the baseline so "how much is done" reads from the left.
const STACK_ORDER: FootageStatus[] = ["delivered", "edited", "shot", "planned"];
const ROW_HEIGHT = 32;

/** Horizontal stacked bars: one row per event, segments = bouts in each footage status. */
export function FootageChart({ rows }: { rows: FootageSummary[] }) {
  const palette = usePalette();
  const withBouts = rows.filter((row) => row.total > 0);
  const hidden = rows.length - withBouts.length;

  if (withBouts.length === 0) {
    return <p className="muted">No bouts announced for these events yet.</p>;
  }

  return (
    <figure className="chart">
      <ul className="legend" aria-label="Footage status">
        {STACK_ORDER.map((status) => (
          <li key={status}>
            <span className="swatch" style={{ background: palette.stages[status] }} />
            {capitalize(status)}
          </li>
        ))}
      </ul>
      <ResponsiveContainer width="100%" height={withBouts.length * ROW_HEIGHT + 40}>
        <BarChart
          data={withBouts}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 0 }}
          barSize={18}
        >
          <CartesianGrid horizontal={false} stroke={palette.grid} />
          <XAxis
            type="number"
            allowDecimals={false}
            tick={{ fill: palette.textMuted, fontSize: 12 }}
            axisLine={{ stroke: palette.axis }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="event_name"
            width={180}
            tick={{ fill: palette.textSecondary, fontSize: 12 }}
            tickFormatter={shortEventName}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip cursor={{ fill: palette.hover }} content={<ChartTooltip />} />
          {STACK_ORDER.map((status) => (
            <Bar
              key={status}
              dataKey={status}
              stackId="footage"
              fill={palette.stages[status]}
              // A surface-colored outline leaves a thin gap between stacked segments.
              stroke={palette.surface}
              strokeWidth={2}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
      {hidden > 0 && (
        <figcaption className="muted">
          {hidden} event{hidden === 1 ? "" : "s"} with no announced bouts not shown.
        </figcaption>
      )}
    </figure>
  );
}

/** Fit axis labels on one line: "UFC Fight Night: Procházka vs. Stirling" -> "FN: Procházka vs. Stirling". */
function shortEventName(name: string): string {
  const short = name.replace(/^UFC Fight Night:\s*/, "FN: ");
  return short.length > 22 ? `${short.slice(0, 21)}…` : short;
}

function ChartTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload as FootageSummary;
  return (
    <div className="tooltip">
      <strong>{row.event_name}</strong>
      <div className="muted">{formatDate(row.event_date)}</div>
      <table>
        <tbody>
          {STACK_ORDER.map((status) => (
            <tr key={status}>
              <td>{capitalize(status)}</td>
              <td className="num">{row[status]}</td>
            </tr>
          ))}
          <tr className="total">
            <td>Pending</td>
            <td className="num">
              {row.pending} of {row.total}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
