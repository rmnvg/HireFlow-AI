"use client";

import { Bot, Loader2, Pencil, PhoneCall, Plus, Search, UserPlus, Users } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api, errorMessage } from "@/lib/api";
import type { Candidate, HunarAgent, Job } from "@/lib/types";

export default function CandidatesPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [agents, setAgents] = useState<HunarAgent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [phoneCandidate, setPhoneCandidate] = useState<Candidate | null>(null);
  const [callCandidate, setCallCandidate] = useState<Candidate | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [phone, setPhone] = useState("");
  const [manual, setManual] = useState({ name: "", email: "", phone: "" });

  const loadCandidates = useCallback(async (jobId: string) => {
    if (!jobId) { setCandidates([]); return; }
    setLoading(true); setError(null);
    try { setCandidates(await api.listCandidates(jobId)); }
    catch (loadError) { setError(errorMessage(loadError)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    async function loadInitial() {
      setLoading(true); setError(null);
      try {
        const loadedJobs = await api.listJobs();
        setJobs(loadedJobs);
        const queryJob = new URLSearchParams(window.location.search).get("job");
        const initialJob = loadedJobs.find((job) => job.id === queryJob)?.id || loadedJobs[0]?.id || "";
        setSelectedJobId(initialJob);
        if (initialJob) setCandidates(await api.listCandidates(initialJob));
      } catch (loadError) { setError(errorMessage(loadError)); }
      finally { setLoading(false); }
      try {
        const loadedAgents = await api.listAgents();
        setAgents(loadedAgents);
        setSelectedAgentId(loadedAgents[0]?.id || "");
      } catch { /* Calls remain unavailable while candidate management still works. */ }
    }
    void loadInitial();
  }, []);

  async function changeJob(jobId: string) {
    setSelectedJobId(jobId); setNotice(null);
    window.history.replaceState(null, "", jobId ? `/candidates?job=${jobId}` : "/candidates");
    await loadCandidates(jobId);
  }

  async function searchApollo() {
    if (!selectedJobId) return;
    setBusy("apollo"); setError(null); setNotice(null);
    try {
      const result = await api.searchCandidates(selectedJobId);
      setNotice(result.review_note);
      await loadCandidates(selectedJobId);
    } catch (searchError) { setError(errorMessage(searchError)); }
    finally { setBusy(null); }
  }

  async function updatePhone() {
    if (!phoneCandidate) return;
    setBusy("phone"); setError(null);
    try {
      const updated = await api.updateCandidatePhone(phoneCandidate.id, phone.trim());
      setCandidates((current) => current.map((candidate) => candidate.id === updated.id ? updated : candidate));
      setPhoneCandidate(null); setNotice("Candidate phone number updated.");
    } catch (updateError) { setError(errorMessage(updateError)); }
    finally { setBusy(null); }
  }

  async function addManualCandidate() {
    if (!selectedJobId) return;
    setBusy("manual"); setError(null);
    try {
      const created = await api.createManualCandidate({ job_id: selectedJobId, ...manual });
      setCandidates((current) => [created, ...current]);
      setManual({ name: "", email: "", phone: "" }); setManualOpen(false);
      setNotice("Manual candidate added.");
    } catch (createError) { setError(errorMessage(createError)); }
    finally { setBusy(null); }
  }

  async function startCall() {
    if (!callCandidate || !selectedAgentId) return;
    setBusy(`call-${callCandidate.id}`); setError(null);
    try {
      await api.createCall(callCandidate.id, selectedAgentId);
      setNotice(`AI screening call initiated for ${callCandidate.name}.`);
      setCallCandidate(null);
    } catch (callError) { setError(errorMessage(callError)); }
    finally { setBusy(null); }
  }

  return (
    <div>
      <PageHeader actions={<Button disabled={!selectedJobId} onClick={() => setManualOpen(true)} variant="outline"><UserPlus className="size-4" /> Add manually</Button>} description="Review sourced profiles, complete contact details and initiate transparent AI screening calls." eyebrow="Talent pool" title="Candidates" />
      <Alert><strong>Apollo scope:</strong> candidate search only checks contacts already saved in your Apollo workspace. Results are suggestions for recruiter review, not guaranteed job matches.</Alert>

      <Card className="mt-5 border-slate-200 p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
          <label className="min-w-0 flex-1"><span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-500">Filter by job</span><select className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-violet-500" onChange={(event) => void changeJob(event.target.value)} value={selectedJobId}><option value="">Select a job</option>{jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select></label>
          <label className="min-w-0 flex-1"><span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-slate-500">AI screening agent</span><select className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-violet-500" onChange={(event) => setSelectedAgentId(event.target.value)} value={selectedAgentId}><option value="">No Hunar agent available</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name || agent.agent_name || agent.id}</option>)}</select></label>
          <Button disabled={!selectedJobId || busy === "apollo"} onClick={() => void searchApollo()}><Search className="size-4" />{busy === "apollo" ? "Searching…" : "Search saved contacts"}</Button>
        </div>
      </Card>

      <div className="mt-4 space-y-3">{error ? <Alert variant="error">{error}</Alert> : null}{notice ? <Alert variant="success">{notice}</Alert> : null}</div>
      <Card className="mt-5 overflow-hidden border-slate-200 shadow-sm">
        {loading ? <div className="space-y-3 p-6">{Array.from({ length: 6 }, (_, index) => <Skeleton className="h-14" key={index} />)}</div> : candidates.length === 0 ? (
          <EmptyState action={jobs.length === 0 ? <Button asChild><Link href="/jobs/new"><Plus className="size-4" /> Create a job</Link></Button> : <Button onClick={() => void searchApollo()}><Search className="size-4" /> Search saved contacts</Button>} description={jobs.length === 0 ? "Create and analyze a job before sourcing candidates." : "Search the selected job against contacts saved in Apollo, or add a candidate manually."} icon={Users} title="No candidates to review" />
        ) : (
          <div className="overflow-x-auto"><table className="w-full min-w-[1120px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Name</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Company</th><th className="px-5 py-3">Location</th><th className="px-5 py-3">Email</th><th className="px-5 py-3">Phone</th><th className="px-5 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">{candidates.map((candidate) => (
            <tr className="hover:bg-slate-50/60" key={candidate.id}><td className="px-5 py-4"><div className="font-medium text-slate-900">{candidate.name}</div><Badge className="mt-1 bg-slate-100 text-slate-600">{candidate.source}</Badge></td><td className="px-5 py-4 text-slate-600">{candidate.current_title || "—"}</td><td className="px-5 py-4 text-slate-600">{candidate.company || "—"}</td><td className="px-5 py-4 text-slate-600">{candidate.location || "—"}</td><td className="px-5 py-4 text-slate-600">{candidate.email || "—"}</td><td className="px-5 py-4"><span className="text-slate-600">{candidate.phone || "Missing"}</span><button aria-label={`Edit phone for ${candidate.name}`} className="ml-2 text-violet-600" onClick={() => { setPhoneCandidate(candidate); setPhone(candidate.phone || ""); }}><Pencil className="size-3.5" /></button></td><td className="px-5 py-4 text-right"><Button disabled={!candidate.phone || !selectedAgentId || busy === `call-${candidate.id}`} onClick={() => setCallCandidate(candidate)} size="sm"><Bot className="size-4" /> Start AI Screening</Button></td></tr>
          ))}</tbody></table></div>
        )}
      </Card>

      <Dialog description="Use E.164 format, including country code, so Hunar can place the call." onClose={() => setPhoneCandidate(null)} open={phoneCandidate !== null} title="Edit phone number"><div className="space-y-4"><Input autoFocus onChange={(event) => setPhone(event.target.value)} placeholder="+919876543210" value={phone} /><div className="flex justify-end gap-2"><Button onClick={() => setPhoneCandidate(null)} variant="outline">Cancel</Button><Button disabled={!/^\+[1-9]\d{7,14}$/.test(phone) || busy === "phone"} onClick={() => void updatePhone()}>{busy === "phone" ? <Loader2 className="size-4 animate-spin" /> : null} Save phone</Button></div></div></Dialog>

      <Dialog description="Add a candidate who is not available in your saved Apollo contacts." onClose={() => setManualOpen(false)} open={manualOpen} title="Add manual candidate"><div className="space-y-4"><Input onChange={(event) => setManual({ ...manual, name: event.target.value })} placeholder="Full name" value={manual.name} /><Input onChange={(event) => setManual({ ...manual, email: event.target.value })} placeholder="Email address" type="email" value={manual.email} /><Input onChange={(event) => setManual({ ...manual, phone: event.target.value })} placeholder="Phone in E.164 format" value={manual.phone} /><div className="flex justify-end gap-2"><Button onClick={() => setManualOpen(false)} variant="outline">Cancel</Button><Button disabled={!manual.name || !manual.email || !/^\+[1-9]\d{7,14}$/.test(manual.phone) || busy === "manual"} onClick={() => void addManualCandidate()}>{busy === "manual" ? <Loader2 className="size-4 animate-spin" /> : null} Add candidate</Button></div></div></Dialog>

      <Dialog description="This is an automated phone call placed by the selected Hunar AI voice agent—not a human recruiter." onClose={() => setCallCandidate(null)} open={callCandidate !== null} title="Confirm AI screening call"><div className="rounded-xl bg-violet-50 p-4"><div className="flex gap-3"><span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white"><Bot className="size-5" /></span><div><p className="font-semibold text-slate-900">AI agent will call {callCandidate?.name}</p><p className="mt-1 text-sm text-slate-600">Number: {callCandidate?.phone}</p></div></div></div><div className="mt-5 flex justify-end gap-2"><Button onClick={() => setCallCandidate(null)} variant="outline">Cancel</Button><Button disabled={!selectedAgentId || busy?.startsWith("call-")} onClick={() => void startCall()}>{busy?.startsWith("call-") ? <Loader2 className="size-4 animate-spin" /> : <PhoneCall className="size-4" />} Confirm AI call</Button></div></Dialog>
    </div>
  );
}
