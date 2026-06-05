"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { UploadResponse } from "@/types";

interface TransactionTableProps {
  uploadResult: UploadResponse | null;
}

function getRiskScoreCardClasses(riskScore: number): string {
  if (riskScore > 65) {
    return "border-red-200 bg-red-50";
  }
  if (riskScore > 40) {
    return "border-amber-200 bg-amber-50";
  }
  return "border-green-200 bg-green-50";
}

export function TransactionTable({ uploadResult }: TransactionTableProps) {
  if (uploadResult === null) {
    return (
      <p className="flex items-center justify-center py-12 text-muted-foreground">
        Upload a CSV to see transactions
      </p>
    );
  }

  const { risk_score, anomalous_count, upload_id } = uploadResult;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-3">
          <Card className={cn(getRiskScoreCardClasses(risk_score))}>
            <CardContent className="space-y-1 pt-4">
              <p className="text-sm text-muted-foreground">Risk Score</p>
              <p className="text-2xl font-bold">{risk_score.toFixed(1)}</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-1 pt-4">
              <p className="text-sm text-muted-foreground">
                Flagged Transactions
              </p>
              <p className="text-2xl font-bold">{anomalous_count}</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-1 pt-4">
              <p className="text-sm text-muted-foreground">Upload ID</p>
              <p className="text-2xl font-bold">{upload_id.slice(0, 8)}</p>
            </CardContent>
          </Card>
        </div>
      </CardContent>
    </Card>
  );
}
