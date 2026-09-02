"use client";

import { ArrowRight, BriefcaseBusiness, Loader2, Search, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import type { Job, JobAnalysis } from "@/lib/types";

export default function NewJobPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [analysis, setAnalysis] = useState<JobAnalysis | null>(null);
  const [skills, setSkills] = useState("");
  const [location, setLocation] = useState("");
  const [minimumExperience, setMinimumExperience] = useState("");
  const [maximumExperience, setMaximumExperience] = useState("");
  const [savedJob, setSavedJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState<"analyze" | "save" | "find" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function analyze() {
    if (description.trim().length < 20) {
      setError("Add at least 20 characters of job description before analyzing.");
      return;
    }
    setBusy("analyze"); setError(null); setSuccess(null);
    try {
      const extracted = await api.analyzeJob(description.trim());
      setAnalysis(extracted);
      setTitle(extracted.job_title || title);
      setSkills(extracted.skills.join(", "));
      setLocation(extracted.location || "");
      setMinimumExperience(extracted.minimum_experience?.toString() || "");
      setMaximumExperience(extracted.maximum_experience?.toString() || "");
      setSavedJob(null);
      setSuccess("Analysis complete. Review and edit the extracted requirements before saving.");
    } catch (analysisError) {
      setError(errorMessage(analysisError));
    } finally { setBusy(null); }
  }

  function editedAnalysis(): JobAnalysis {
    if (!analysis) throw new Error("Analyze the job description before saving.");
    return {
      ...analysis,
      job_title: title.trim(),
      skills: skills.split(",").map((skill) => skill.trim()).filter(Boolean),
      location: location.trim() || null,
      minimum_experience: minimumExperience === "" ? null : Number(minimumExperience),
      maximum_experience: maximumExperience === "" ? null : Number(maximumExperience),
    };
  }

  async function save(): Promise<Job | null> {
    setBusy("save"); setError(null); setSuccess(null);
    try {
      if (!title.trim()) throw new Error("Job title is required.");
      const job = await api.createJob(description.trim(), editedAnalysis());
      setSavedJob(job);
      setSuccess("Job saved. You can now search your saved Apollo contacts.");
      return job;
    } catch (saveError) {
      setError(errorMessage(saveError));
      return null;
    } finally { setBusy(null); }
  }

  async function findCandidates() {
    setError(null); setSuccess(null);
    let job = savedJob;
    if (!job) job = await save();
    if (!job) return;
    setBusy("find");
    try {
      await api.searchCandidates(job.id);
      router.push(`/candidates?job=${job.id}`);
    } catch (searchError) {
      setError(errorMessage(searchError));
    } finally { setBusy(null); }
  }

  const working = busy !== null;
  return (
    <div>
      <PageHeader description="Turn a full job description into structured, editable search requirements." eyebrow="Jobs" title="Create a new job" />
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="border-slate-200 shadow-sm">
          <CardHeader><CardTitle className="flex items-center gap-2"><BriefcaseBusiness className="size-5 text-violet-600" /> Job details</CardTitle></CardHeader>
          <CardContent className="space-y-5">
            <Field label="Job title"><Input onChange={(event) => { setTitle(event.target.value); setSavedJob(null); }} placeholder="Senior Python Backend Engineer" value={title} /></Field>
            <Field label="Full job description"><Textarea className="min-h-72" onChange={(event) => { setDescription(event.target.value); setAnalysis(null); setSavedJob(null); }} placeholder="Paste responsibilities, experience, skills, location and role context…" value={description} /></Field>
            <Button disabled={working || description.trim().length < 20} onClick={() => void analyze()} type="button">
              {busy === "analyze" ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />} Analyze JD
            </Button>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardHeader><div className="flex items-center justify-between gap-3"><CardTitle>Extracted requirements</CardTitle><Badge>{analysis ? "Ready to edit" : "Awaiting analysis"}</Badge></div></CardHeader>
          <CardContent>
            {!analysis ? <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-16 text-center"><Sparkles className="mx-auto size-7 text-slate-400" /><p className="mt-3 font-medium text-slate-700">AI-extracted details appear here</p><p className="mt-1 text-sm leading-6 text-slate-500">Nothing is saved until you review and confirm it.</p></div> : (
              <div className="space-y-5">
                <Field hint="Comma-separated; edit freely." label="Skills"><Textarea className="min-h-24" onChange={(event) => { setSkills(event.target.value); setSavedJob(null); }} value={skills} /></Field>
                <Field label="Location"><Input onChange={(event) => { setLocation(event.target.value); setSavedJob(null); }} placeholder="Optional" value={location} /></Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Minimum experience"><Input min="0" onChange={(event) => { setMinimumExperience(event.target.value); setSavedJob(null); }} placeholder="Years" type="number" value={minimumExperience} /></Field>
                  <Field label="Maximum experience"><Input min="0" onChange={(event) => { setMaximumExperience(event.target.value); setSavedJob(null); }} placeholder="Years" type="number" value={maximumExperience} /></Field>
                </div>
                {analysis.seniority ? <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2.5 text-sm"><span className="text-slate-500">Seniority</span><span className="font-medium text-slate-800">{analysis.seniority}</span></div> : null}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-5 space-y-3">{error ? <Alert variant="error">{error}</Alert> : null}{success ? <Alert variant="success">{success}</Alert> : null}</div>
      <div className="mt-6 flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-6">
        <Button disabled={!analysis || working} onClick={() => void save()} variant="outline">{busy === "save" ? <Loader2 className="size-4 animate-spin" /> : null} Save Job</Button>
        <Button disabled={!analysis || working} onClick={() => void findCandidates()}>{busy === "find" ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />} Find Candidates <ArrowRight className="size-4" /></Button>
      </div>
    </div>
  );
}

function Field({ children, hint, label }: { children: React.ReactNode; hint?: string; label: string }) {
  return <label className="block"><span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span>{children}{hint ? <span className="mt-1 block text-xs text-slate-500">{hint}</span> : null}</label>;
}
