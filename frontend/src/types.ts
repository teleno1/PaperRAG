export type ReportLanguage = "zh" | "en";
export type EvidenceReadiness =
  | "awaiting_authorised_file"
  | "importing"
  | "parsing"
  | "indexing"
  | "ready"
  | "failed"
  | "unavailable";
export type OperationStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "interrupted"
  | "cancelled";

export interface WorkspaceOperation {
  id: string;
  workspace_id: string;
  paper_id: string | null;
  operation_type: string;
  status: OperationStatus;
  phase: string;
  error_category: string | null;
  error_message: string | null;
  retry_action: string | null;
  completed_work: number;
  total_work: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface ResearchPaper {
  id: string;
  workspace_id: string;
  title: string;
  source_kind: "upload" | "discovery";
  original_filename: string;
  selected: boolean;
  evidence_readiness: EvidenceReadiness;
  evidence_eligible: boolean;
  active_document_version_id: string | null;
  authors: string[];
  year: string;
  venue: string;
  failure_phase: string | null;
  failure_message: string | null;
  retryable: boolean;
  next_action: string | null;
  doi: string | null;
  abstract: string;
  published_at: string | null;
  source_updated_at: string | null;
  source_url: string | null;
  pdf_url: string | null;
  pdf_urls: string[];
  is_open_access: boolean | null;
  license: string | null;
  source_links: string[];
  discovery_query: string | null;
  discovered_at: string | null;
  dismissed: boolean;
}

export interface ResearchWorkspace {
  id: string;
  topic: string;
  report_language: ReportLanguage;
  state: "setup" | "active" | "archived";
  created_at: string;
  updated_at: string;
  papers: ResearchPaper[];
  operations: WorkspaceOperation[];
  outline: ReportOutline | null;
}

export interface OutlineSection {
  id: string;
  title: string;
  description: string;
}

export interface ReportOutline {
  id: string;
  workspace_id: string;
  revision_number: number;
  status: "draft" | "approved";
  title: string;
  research_question: string;
  sections: OutlineSection[];
  evidence_paper_ids: string[];
  created_at: string;
  updated_at: string;
  approved_at: string | null;
}

export interface DiscoveryResponse {
  provider: "openalex" | "arxiv";
  query: string;
  status: "succeeded" | "empty" | "retryable_error" | "failed";
  candidates: ResearchPaper[];
  page: number;
  per_page: number;
  total_count: number | null;
  next_page: number | null;
  error_message: string | null;
  retryable: boolean;
  retry_after_seconds: number | null;
  next_action: string | null;
}

export interface UploadResponse {
  paper: ResearchPaper;
  operation: WorkspaceOperation | null;
}
