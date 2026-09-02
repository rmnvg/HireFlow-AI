import type {
  ApiErrorBody,
  Call,
  Candidate,
  CandidateSearchResult,
  HunarAgent,
  Job,
  JobAnalysis,
} from "@/lib/types";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

function apiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_URL;
  if (!value) throw new ApiError("NEXT_PUBLIC_API_URL is not configured", 500);
  return value.replace(/\/$/, "");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("Could not reach the HireFlow API", 0);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new ApiError(body.detail || `Request failed with status ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}

function unwrapAgents(payload: unknown): HunarAgent[] {
  if (Array.isArray(payload)) return payload as HunarAgent[];
  if (!payload || typeof payload !== "object") return [];
  const record = payload as Record<string, unknown>;
  if (Array.isArray(record.agents)) return record.agents as HunarAgent[];
  if (Array.isArray(record.results)) return record.results as HunarAgent[];
  if (record.data && typeof record.data === "object") {
    const data = record.data as Record<string, unknown>;
    if (Array.isArray(data.agents)) return data.agents as HunarAgent[];
    if (Array.isArray(data.results)) return data.results as HunarAgent[];
  }
  return [];
}

export const api = {
  listJobs: () => request<Job[]>("/api/jobs"),
  analyzeJob: (description: string) =>
    request<JobAnalysis>("/api/jobs/analyze", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),
  createJob: (description: string, analysis: JobAnalysis) =>
    request<Job>("/api/jobs", {
      method: "POST",
      body: JSON.stringify({ description, ...analysis }),
    }),
  searchCandidates: (jobId: string) =>
    request<CandidateSearchResult>(`/api/jobs/${jobId}/search-candidates`, { method: "POST" }),
  listCandidates: (jobId: string) =>
    request<Candidate[]>(`/api/candidates?job_id=${encodeURIComponent(jobId)}`),
  updateCandidatePhone: (candidateId: string, phone: string) =>
    request<Candidate>(`/api/candidates/${candidateId}/phone`, {
      method: "PATCH",
      body: JSON.stringify({ phone }),
    }),
  createManualCandidate: (payload: { job_id: string; name: string; phone: string; email: string }) =>
    request<Candidate>("/api/candidates/manual", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listAgents: async () => unwrapAgents(await request<unknown>("/api/hunar/agents")),
  createCall: (candidateId: string, agentId: string) =>
    request<Call>("/api/calls", {
      method: "POST",
      body: JSON.stringify({ candidate_id: candidateId, agent_id: agentId }),
    }),
  listCalls: () => request<Call[]>("/api/calls"),
  refreshCall: (callId: string) => request<Call>(`/api/calls/${callId}/refresh`, { method: "POST" }),
};

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}
