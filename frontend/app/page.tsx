"use client";

import { BriefcaseBusiness, CheckCircle2, Headphones, PhoneCall, Sparkles, Users } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, errorMessage } from "@/lib/api";
import { formatDate, isCompleted, isInterested } from "@/lib/presentation";
import type { Call, Candidate, Job } from "@/lib/types";

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedJobs, loadedCalls] = await Promise.all([api.listJobs(), api.listCalls()]);
      const candidateGroups = await Promise.all(loadedJobs.map((job) => api.listCandidates(job.id)));
      setJobs(loadedJobs);
      setCalls(loadedCalls);
      setCandidates(candidateGroups.flat());
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    async function initialize() { await loadDashboard(); }
    void initialize();
  }, [loadDashboard]);

  const jobById = useMemo(() => new Map(jobs.map((job) => [job.id, job])), [jobs]);
  const candidateById = useMemo(() => new Map(candidates.map((candidate) => [candidate.id, candidate])), [candidates]);
  const metrics = [
    { label: "Total jobs", value: jobs.length, icon: BriefcaseBusiness, tone: "bg-violet-50 text-violet-600" },
    { label: "Candidates", value: candidates.length, icon: Users, tone: "bg-blue-50 text-blue-600" },
    { label: "Calls initiated", value: calls.length, icon: PhoneCall, tone: "bg-amber-50 text-amber-600" },
    { label: "Completed calls", value: calls.filter((call) => isCompleted(call.status)).length, icon: CheckCircle2, tone: "bg-emerald-50 text-emerald-600" },
    { label: "Interested", value: calls.filter(isInterested).length, icon: Sparkles, tone: "bg-fuchsia-50 text-fuchsia-600" },
  ];

  return (
    <div>
      <PageHeader actions={<Button asChild><Link href="/jobs/new"><BriefcaseBusiness className="size-4" /> Create a job</Link></Button>} description="Monitor sourcing and AI screening outcomes across your active hiring pipeline." eyebrow="Overview" title="Recruiting dashboard" />
      {error ? <div className="mb-5"><Alert variant="error"><div className="flex flex-wrap items-center gap-3"><span>{error}</span><button className="font-semibold underline" onClick={() => void loadDashboard()}>Try again</button></div></Alert></div> : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {loading ? Array.from({ length: 5 }, (_, index) => <Skeleton className="h-32" key={index} />) : metrics.map(({ icon: Icon, label, tone, value }) => (
          <Card className="border-slate-200 shadow-sm" key={label}><CardContent className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value}</p></div><span className={`flex size-10 items-center justify-center rounded-xl ${tone}`}><Icon className="size-5" /></span></div></CardContent></Card>
        ))}
      </section>

      <Card className="mt-6 overflow-hidden border-slate-200 shadow-sm">
        <CardHeader className="flex-row items-center justify-between space-y-0 border-b border-slate-100"><div><CardTitle>Recent AI calls</CardTitle><p className="mt-1 text-sm text-slate-500">Latest candidate screening activity from Hunar</p></div><Button asChild size="sm" variant="outline"><Link href="/calls">View all</Link></Button></CardHeader>
        {loading ? <div className="space-y-3 p-6">{Array.from({ length: 4 }, (_, index) => <Skeleton className="h-12" key={index} />)}</div> : calls.length === 0 ? (
          <EmptyState action={<Button asChild variant="outline"><Link href="/candidates">Browse candidates</Link></Button>} description="Start an AI screening call from the candidates page and it will appear here." icon={Headphones} title="No calls initiated yet" />
        ) : (
          <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-6 py-3 font-semibold">Candidate</th><th className="px-6 py-3 font-semibold">Job</th><th className="px-6 py-3 font-semibold">Status</th><th className="px-6 py-3 font-semibold">Interest</th><th className="px-6 py-3 font-semibold">Initiated</th></tr></thead><tbody className="divide-y divide-slate-100">{calls.slice(0, 8).map((call) => (
            <tr className="hover:bg-slate-50/70" key={call.id}><td className="px-6 py-4 font-medium text-slate-900">{candidateById.get(call.candidate_id)?.name || "Unknown candidate"}</td><td className="px-6 py-4 text-slate-600">{jobById.get(call.job_id)?.title || "Unknown job"}</td><td className="px-6 py-4"><StatusBadge status={call.status} /></td><td className="px-6 py-4 text-slate-600">{isInterested(call) ? "Interested" : "—"}</td><td className="px-6 py-4 text-slate-500">{formatDate(call.created_at)}</td></tr>
          ))}</tbody></table></div>
        )}
      </Card>
    </div>
  );
}
