"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { RiskScore } from "@/types";

interface RiskTimelineProps {
  riskScores: RiskScore[];
}

interface ChartDataPoint {
  date: string;
  score: number;
  id: string;
}

function formatDate(scoredAt: string): string {
  return new Date(scoredAt).toLocaleDateString("en-US", {
    month: "short",
    day: "2-digit",
  });
}

function transformRiskScores(riskScores: RiskScore[]): ChartDataPoint[] {
  return [...riskScores]
    .sort(
      (a, b) =>
        new Date(a.scored_at).getTime() - new Date(b.scored_at).getTime(),
    )
    .map((item) => ({
      date: formatDate(item.scored_at),
      score: item.score,
      id: item.id,
    }));
}

function getDotFill(score: number): string {
  if (score > 80) return "#ef4444";
  if (score > 65) return "#f59e0b";
  return "#3b82f6";
}

function renderDot(props: Record<string, unknown>) {
  const cx = props.cx as number | undefined;
  const cy = props.cy as number | undefined;
  const payload = props.payload as ChartDataPoint | undefined;
  if (cx == null || cy == null || payload == null) return null;
  return <circle cx={cx} cy={cy} r={4} fill={getDotFill(payload.score)} />;
}

export function RiskTimeline({ riskScores }: RiskTimelineProps) {
  const chartData = transformRiskScores(riskScores);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="flex h-[300px] items-center justify-center text-muted-foreground">
            No data yet
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis domain={[0, 100]} />
              <Tooltip
                formatter={(value) => [value ?? 0, "Score"]}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <ReferenceLine
                y={65}
                stroke="#f59e0b"
                strokeDasharray="4 4"
                label="Threshold"
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={renderDot}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
