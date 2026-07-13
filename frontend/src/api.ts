import type {
  DiscoveryResponse,
  ResearchWorkspace,
  ReportOutline,
  ReportLanguage,
  UploadResponse,
  WorkspaceOperation,
} from "./types";

interface ApiErrorPayload {
  detail?: string;
  error?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    throw new Error(payload.detail || payload.error || `请求失败（${response.status}）`);
  }
  return (await response.json()) as T;
}

export function listWorkspaces(): Promise<ResearchWorkspace[]> {
  return request<ResearchWorkspace[]>("/api/workspaces");
}

export function getWorkspace(workspaceId: string): Promise<ResearchWorkspace> {
  return request<ResearchWorkspace>(`/api/workspaces/${workspaceId}`);
}

export function createWorkspace(topic: string, reportLanguage: ReportLanguage): Promise<ResearchWorkspace> {
  return request<ResearchWorkspace>("/api/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, report_language: reportLanguage }),
  });
}

export function discoverPapers(
  workspaceId: string,
  query: string,
  provider: "openalex" | "arxiv",
): Promise<DiscoveryResponse> {
  return request<DiscoveryResponse>(`/api/workspaces/${workspaceId}/papers/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, provider }),
  });
}

export function importPaper(workspaceId: string, paperId: string): Promise<UploadResponse> {
  return request<UploadResponse>(`/api/workspaces/${workspaceId}/papers/${paperId}/import`, {
    method: "POST",
  });
}

export function selectPaper(workspaceId: string, paperId: string): Promise<void> {
  return request(`/api/workspaces/${workspaceId}/papers/${paperId}/select`, { method: "POST" });
}

export function removePaper(workspaceId: string, paperId: string): Promise<void> {
  return request(`/api/workspaces/${workspaceId}/papers/${paperId}`, { method: "DELETE" });
}

export function retryPaper(workspaceId: string, paperId: string): Promise<UploadResponse> {
  return request<UploadResponse>(`/api/workspaces/${workspaceId}/papers/${paperId}/retry`, {
    method: "POST",
  });
}

export async function uploadPaper(
  workspaceId: string,
  file: File,
  candidateId?: string,
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  if (candidateId) form.append("candidate_id", candidateId);
  return request<UploadResponse>(`/api/workspaces/${workspaceId}/papers/upload`, {
    method: "POST",
    body: form,
  });
}

export function getOperation(operationId: string): Promise<WorkspaceOperation> {
  return request<WorkspaceOperation>(`/api/operations/${operationId}`);
}

export function generateOutline(workspaceId: string): Promise<WorkspaceOperation> {
  return request<WorkspaceOperation>(`/api/workspaces/${workspaceId}/outline/generate`, {
    method: "POST",
  });
}

export function saveOutline(
  workspaceId: string,
  outline: Pick<ReportOutline, "id" | "title" | "research_question" | "sections">,
): Promise<ReportOutline> {
  return request<ReportOutline>(`/api/workspaces/${workspaceId}/outline`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      revision_id: outline.id,
      title: outline.title,
      research_question: outline.research_question,
      sections: outline.sections,
    }),
  });
}

export function approveOutline(workspaceId: string, revisionId: string): Promise<ReportOutline> {
  return request<ReportOutline>(`/api/workspaces/${workspaceId}/outline/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision_id: revisionId }),
  });
}

export function retryOperation(operationId: string): Promise<WorkspaceOperation> {
  return request<WorkspaceOperation>(`/api/operations/${operationId}/retry`, {
    method: "POST",
  });
}
