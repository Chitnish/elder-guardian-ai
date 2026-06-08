"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"

import { AlertLog } from "@/components/dashboard/AlertLog"
import { CsvUpload } from "@/components/dashboard/CsvUpload"
import { NarrativeCard } from "@/components/dashboard/NarrativeCard"
import { RiskTimeline } from "@/components/dashboard/RiskTimeline"
import { TransactionTable } from "@/components/dashboard/TransactionTable"
import { Button } from "@/components/ui/button"
import { getDashboard } from "@/lib/api"
import { createClient } from "@/lib/supabase"
import type { DashboardData, UploadResponse } from "@/types"

export default function DashboardPage() {
  const router = useRouter()
  const [userId, setUserId] = useState<string | null>(null)
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchDashboard = useCallback(async (uid: string) => {
    try {
      const result = await getDashboard(uid)
      setDashboardData(result)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load dashboard"
      setError(message)
    }
  }, [])

  useEffect(() => {
    async function init() {
      const supabase = createClient()
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session) {
        router.push("/login")
        return
      }

      setUserId(session.user.id)
      await fetchDashboard(session.user.id)
      setIsLoading(false)

      const { data: contacts } = await supabase
        .from("emergency_contacts")
        .select("id")
        .eq("user_id", session.user.id)
        .limit(1)

      if (!contacts || contacts.length === 0) {
        router.push("/onboarding")
        return
      }
    }

    void init()
  }, [router, fetchDashboard])

  async function handleUploadComplete(result: UploadResponse) {
    setUploadResult(result)
    if (userId) {
      await fetchDashboard(userId)
    }
  }

  async function handleSignOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push("/login")
  }

  return (
    <div className="min-h-screen">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <h1 className="text-xl font-semibold">Elder Guardian AI</h1>
          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <Link href="/onboarding">Edit Contact</Link>
            </Button>
            <Button variant="outline" onClick={() => void handleSignOut()}>
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      {isLoading ? (
        <div className="flex min-h-[50vh] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-blue-500" />
        </div>
      ) : (
        <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8">
          {userId && (
            <CsvUpload
              userId={userId}
              onUploadComplete={handleUploadComplete}
            />
          )}
          <NarrativeCard
            narrative={uploadResult?.narrative ?? ""}
            riskScore={uploadResult?.risk_score ?? 0}
          />
          <RiskTimeline riskScores={dashboardData?.risk_scores ?? []} />
          <TransactionTable uploadResult={uploadResult} />
          <AlertLog alerts={dashboardData?.alerts ?? []} />
          {error && <p className="text-sm text-red-600">{error}</p>}
        </main>
      )}
    </div>
  )
}
