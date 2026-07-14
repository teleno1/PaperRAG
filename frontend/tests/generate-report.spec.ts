import { expect, test } from "@playwright/test";

const workspaceId = "workspace-report-1";
const paperId = "paper-report-1";
const reportId = "report-1";
const claimId = "claim-1";
const citationId = "citation-1";

function paper() {
  return {
    id: paperId,
    workspace_id: workspaceId,
    title: "A traceable paper",
    source_kind: "upload",
    original_filename: "paper.pdf",
    selected: true,
    evidence_readiness: "ready",
    evidence_eligible: true,
    active_document_version_id: "version-1",
    authors: ["Researcher One"],
    year: "2025",
    venue: "Open Venue",
    failure_phase: null,
    failure_message: null,
    retryable: false,
    next_action: null,
    doi: null,
    abstract: "",
    published_at: null,
    source_updated_at: null,
    source_url: null,
    pdf_url: null,
    pdf_urls: [],
    is_open_access: null,
    license: null,
    source_links: [],
    discovery_query: null,
    discovered_at: null,
    dismissed: false,
  };
}

function outline() {
  return {
    id: "outline-report-1",
    workspace_id: workspaceId,
    revision_number: 1,
    status: "approved",
    title: "Traceable evidence review",
    research_question: "How can evidence remain traceable?",
    sections: [{ id: "findings", title: "Findings", description: "Evidence" }],
    evidence_paper_ids: [paperId],
    created_at: "2026-07-14T00:00:00Z",
    updated_at: "2026-07-14T00:00:00Z",
    approved_at: "2026-07-14T00:00:00Z",
  };
}

function report(claimText = "Generated grounded Claim") {
  return {
    id: reportId,
    workspace_id: workspaceId,
    outline_revision_id: "outline-report-1",
    title: "Traceable evidence review",
    language: "en",
    overview: "A grounded report overview",
    sections: [{
      id: "findings",
      title: "Findings",
      claims: [{
        id: claimId,
        section_id: "findings",
        text: claimText,
        claim_type: "supported",
        citations: [{ id: citationId, claim_id: claimId, source_chunk_ids: ["chunk-1"], review_state: "verified" }],
      }],
    }],
    source_chunks: [{
      id: "chunk-1",
      workspace_id: workspaceId,
      paper_id: paperId,
      document_version_id: "version-1",
      chunk_id: "chunk-1",
      title: "A traceable paper",
      excerpt: "Evidence remains traceable when claims retain source links.",
      section: "Findings",
      authors: ["Researcher One"],
      year: "2025",
      venue: "Open Venue",
      page_start: null,
      page_end: null,
    }],
    evidence_coverage: {
      selected_paper_ids: [paperId],
      included_paper_ids: [paperId],
      excluded_papers: [],
      used_ready_subset: false,
    },
    gap_notes: [],
    status: "ready",
    created_at: "2026-07-14T00:00:00Z",
    updated_at: "2026-07-14T00:00:00Z",
  };
}

test("researcher can generate and auto-save an editable cited report", async ({ page }) => {
  let generated = false;
  let currentReport = null as ReturnType<typeof report> | null;
  const currentOperation = {
    id: "report-operation-1",
    workspace_id: workspaceId,
    paper_id: null,
    operation_type: "generate_report",
    status: "succeeded",
    phase: "draft_ready",
    error_category: null,
    error_message: null,
    retry_action: null,
    completed_work: 1,
    total_work: 1,
    started_at: "2026-07-14T00:00:00Z",
    finished_at: "2026-07-14T00:00:01Z",
  };
  const workspace = () => ({
    id: workspaceId,
    topic: "Traceable research evidence",
    report_language: "en",
    state: "active",
    created_at: "2026-07-14T00:00:00Z",
    updated_at: "2026-07-14T00:00:00Z",
    papers: [paper()],
    operations: generated ? [currentOperation] : [],
    outline: outline(),
    report: currentReport,
  });

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (request.method() === "GET" && path === "/api/workspaces") {
      await route.fulfill({ json: [workspace()] });
      return;
    }
    if (request.method() === "GET" && path === `/api/workspaces/${workspaceId}`) {
      await route.fulfill({ json: workspace() });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/report/generate`) {
      generated = true;
      currentReport = report();
      await route.fulfill({ status: 202, json: currentOperation });
      return;
    }
    if (request.method() === "PUT" && path === `/api/workspaces/${workspaceId}/report`) {
      currentReport = JSON.parse(request.postData() || "null");
      await route.fulfill({ json: currentReport });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: "not mocked" } });
  });

  await page.goto("/");
  await page.getByTestId("report-generate").click();
  await expect(page.getByTestId("report-status")).toContainText("证据已关联");
  await expect(page.getByTestId(`claim-citations-${claimId}`)).toContainText("1");

  const claim = page.getByTestId(`report-claim-${claimId}`);
  await claim.fill("Researcher edited Claim");
  await expect.poll(() => currentReport?.sections[0].claims[0].text).toBe("Researcher edited Claim");
  await page.reload();
  await expect(page.getByTestId(`report-claim-${claimId}`)).toHaveValue("Researcher edited Claim");
  await expect(page.getByTestId(`claim-citations-${claimId}`)).toContainText("1");
});
