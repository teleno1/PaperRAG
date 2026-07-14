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
  report: LiteratureReport | null;
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

export interface SourceChunk {
  id: string;
  workspace_id: string;
  paper_id: string;
  document_version_id: string;
  chunk_id: string;
  title: string;
  excerpt: string;
  section: string;
  authors: string[];
  year: string;
  venue: string;
  page_start: number | null;
  page_end: number | null;
}

export interface ClaimCitation {
  id: string;
  claim_id: string;
  source_chunk_ids: string[];
  review_state: "verified" | "pending_review" | "user_confirmed" | "evidence_unavailable";
}

export interface ReportClaim {
  id: string;
  section_id: string;
  text: string;
  claim_type: "supported" | "evidence_gap";
  citations: ClaimCitation[];
}

export interface LiteratureReportSection {
  id: string;
  title: string;
  claims: ReportClaim[];
}

export interface EvidenceCoverage {
  selected_paper_ids: string[];
  included_paper_ids: string[];
  excluded_papers: Array<{ paper_id: string; reason: string }>;
  used_ready_subset: boolean;
}

export interface LiteratureReport {
  id: string;
  workspace_id: string;
  outline_revision_id: string;
  title: string;
  language: ReportLanguage;
  overview: string;
  sections: LiteratureReportSection[];
  source_chunks: SourceChunk[];
  evidence_coverage: EvidenceCoverage;
  gap_notes: string[];
  status: "ready" | "needs_attention";
  created_at: string;
  updated_at: string;
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
