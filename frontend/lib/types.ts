export interface Job {
  id: string;
  title: string;
  description: string;
  location: string | null;
  minimum_experience: number | null;
  maximum_experience: number | null;
  skills: string[];
  parsed_requirements: {
    seniority?: string | null;
    search_keywords?: string;
    [key: string]: unknown;
  };
  created_at: string;
}

export interface JobAnalysis {
  job_title: string;
  skills: string[];
  location: string | null;
  minimum_experience: number | null;
  maximum_experience: number | null;
  seniority: string | null;
  search_keywords: string;
}

export interface Candidate {
  id: string;
  job_id: string;
  apollo_id: string | null;
  name: string;
  current_title: string | null;
  company: string | null;
  location: string | null;
  email: string | null;
  phone: string | null;
  source: string;
  raw_profile: Record<string, unknown>;
  created_at: string;
}

export interface Call {
  id: string;
  job_id: string;
  candidate_id: string;
  hunar_call_id: string | null;
  request_id: string;
  status: string;
  result: Record<string, unknown> | null;
  summary: string | null;
  recording_url: string | null;
  duration_seconds: number | null;
  raw_response: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface HunarAgent {
  id: string;
  name?: string;
  agent_name?: string;
  [key: string]: unknown;
}

export interface CandidateSearchResult {
  job_id: string;
  search_keywords: string;
  fallback_without_keywords: boolean;
  review_note: string;
  candidates: Candidate[];
}

export interface ApiErrorBody {
  detail?: string;
}
