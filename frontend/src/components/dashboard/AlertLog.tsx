"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Alert } from "@/types";

interface AlertLogProps {
  alerts: Alert[];
}

function formatSentAt(sentAt: string): string {
  return new Date(sentAt).toLocaleDateString();
}

function StatusBadge({ status }: { status: string }) {
  if (status === "sent") {
    return (
      <Badge className="border-transparent bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
        Sent
      </Badge>
    );
  }
  if (status === "mocked") {
    return (
      <Badge className="border-transparent bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
        Mocked
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <Badge className="border-transparent bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
        Failed
      </Badge>
    );
  }
  return <Badge variant="outline">{status}</Badge>;
}

export function AlertLog({ alerts }: AlertLogProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Alert Log</CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="text-muted-foreground">No alerts sent yet</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>SMS</TableHead>
                <TableHead>Email</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell>{formatSentAt(alert.sent_at)}</TableCell>
                  <TableCell>{alert.contact_name}</TableCell>
                  <TableCell>
                    <StatusBadge status={alert.sms_status} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={alert.email_status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
