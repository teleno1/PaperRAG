import type {
  DiscoveryResponse,
  ResearchWorkspace,
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
