"use client";

import { ExternalLink, Headphones, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, errorMessage } from "@/lib/api";
import { formatDate, formatDuration, resultValue } from "@/lib/presentation";
import type { Call, Candidate, Job } from "@/lib/types";

export default function CallsPage() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [loadedJobs, loadedCalls] = await Promise.all([api.listJobs(), api.listCalls()]);
      const candidateGroups = await Promise.all(loadedJobs.map((job) => api.listCandidates(job.id)));
      setJobs(loadedJobs); setCalls(loadedCalls); setCandidates(candidateGroups.flat());
    } catch (loadError) { setError(errorMessage(loadError)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    async function initialize() { await load(); }
    void initialize();
  }, [load]);
  const jobById = useMemo(() => new Map(jobs.map((job) => [job.id, job])), [jobs]);
  const candidateById = useMemo(() => new Map(candidates.map((candidate) => [candidate.id, candidate])), [candidates]);

  async function refresh(callId: string) {
    setRefreshing(callId); setError(null);
    try {
      const updated = await api.refreshCall(callId);
      setCalls((current) => current.map((call) => call.id === updated.id ? updated : call));
    } catch (refreshError) { setError(errorMessage(refreshError)); }
    finally { setRefreshing(null); }
  }

  return (
    <div>
      <PageHeader actions={<Button onClick={() => void load()} variant="outline"><RefreshCw className="size-4" /> Reload all</Button>} description="Review Hunar AI screening outcomes, recruiter-ready insights and call recordings." eyebrow="Voice screening" title="AI screening calls" />
      <Alert><strong>AI disclosure:</strong> every call shown here is placed by a Hunar AI voice agent. Refresh retrieves the latest provider status and screening output.</Alert>
      {error ? <div className="mt-4"><Alert variant="error">{error}</Alert></div> : null}

      <Card className="mt-5 overflow-hidden border-slate-200 shadow-sm">
        {loading ? <div className="space-y-3 p-6">{Array.from({ length: 6 }, (_, index) => <Skeleton className="h-16" key={index} />)}</div> : calls.length === 0 ? (
          <EmptyState action={<Button asChild><Link href="/candidates">Start from candidates</Link></Button>} description="Choose a candidate and confirm an AI screening call to begin collecting structured insights." icon={Headphones} title="No screening calls yet" />
        ) : (
          <div className="overflow-x-auto"><table className="w-full min-w-[1760px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-3">Candidate</th><th className="px-4 py-3">Job</th><th className="px-4 py-3">Hunar status</th><th className="px-4 py-3">Interest</th><th className="px-4 py-3">Duration</th><th className="px-4 py-3">Notice period</th><th className="px-4 py-3">Expected compensation</th><th className="px-4 py-3">Interview availability</th><th className="px-4 py-3">Summary</th><th className="px-4 py-3">Recording</th><th className="px-4 py-3">Updated</th><th className="px-4 py-3 text-right">Action</th></tr></thead><tbody className="divide-y divide-slate-100">{calls.map((call) => (
            <tr className="align-top hover:bg-slate-50/60" key={call.id}>
              <td className="px-4 py-4 font-medium text-slate-900">{candidateById.get(call.candidate_id)?.name || "Unknown candidate"}</td>
              <td className="px-4 py-4 text-slate-600">{jobById.get(call.job_id)?.title || "Unknown job"}</td>
              <td className="px-4 py-4"><StatusBadge status={call.status} /></td>
              <td className="px-4 py-4"><Badge className="bg-blue-50 text-blue-700">{resultValue(call, "interest", "interest_level", "interested")}</Badge></td>
              <td className="px-4 py-4 text-slate-600">{formatDuration(call.duration_seconds)}</td>
              <td className="px-4 py-4 text-slate-600">{resultValue(call, "notice_period", "noticePeriod")}</td>
              <td className="px-4 py-4 text-slate-600">{resultValue(call, "expected_compensation", "expected_salary", "compensation")}</td>
              <td className="px-4 py-4 text-slate-600">{resultValue(call, "interview_availability", "availability")}</td>
              <td className="max-w-72 px-4 py-4 leading-5 text-slate-600">{call.summary || "—"}</td>
              <td className="px-4 py-4">{call.recording_url ? <a className="inline-flex items-center gap-1 font-medium text-violet-600 hover:underline" href={call.recording_url} rel="noreferrer" target="_blank">Listen <ExternalLink className="size-3.5" /></a> : "—"}</td>
              <td className="px-4 py-4 text-xs text-slate-500">{formatDate(call.updated_at)}</td>
              <td className="px-4 py-4 text-right"><Button disabled={refreshing === call.id || !call.hunar_call_id} onClick={() => void refresh(call.id)} size="sm" variant="outline"><RefreshCw className={`size-3.5 ${refreshing === call.id ? "animate-spin" : ""}`} /> Refresh</Button></td>
            </tr>
          ))}</tbody></table></div>
        )}
      </Card>
    </div>
  );
}
