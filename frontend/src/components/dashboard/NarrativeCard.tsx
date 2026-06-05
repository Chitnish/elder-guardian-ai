"use client";

import { AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface NarrativeCardProps {
  narrative: string;
  riskScore: number;
}

export function NarrativeCard({ narrative, riskScore }: NarrativeCardProps) {
  if (riskScore <= 65) {
    return null;
  }

  const roundedScore = riskScore.toFixed(1);

  return (
    <Card className="border-amber-200 bg-amber-50">
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-amber-600" />
            <CardTitle>Risk Alert</CardTitle>
          </div>
          <Badge
            variant={riskScore > 80 ? "destructive" : undefined}
            className={riskScore > 80 ? undefined : "bg-amber-500 text-white"}
          >
            Risk Score: {roundedScore}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p>{narrative}</p>
        <p className="text-xs text-muted-foreground">
          This is an early warning, not a diagnosis. Please review transactions
          and consult with your loved one.
        </p>
      </CardContent>
    </Card>
  );
}
