import { expect, test } from "@playwright/test";

const workspaceId = "workspace-1";
const candidateId = "candidate-1";
const operationId = "operation-1";

function paper(overrides: Record<string, unknown> = {}) {
  return {
    id: candidateId,
    workspace_id: workspaceId,
    title: "A traceable paper",
    source_kind: "discovery",
    original_filename: "a-traceable-paper.pdf",
    selected: false,
    evidence_readiness: "unavailable",
    evidence_eligible: false,
    active_document_version_id: null,
    authors: ["Researcher One"],
    year: "2025",
    venue: "Open Venue",
    failure_phase: null,
    failure_message: null,
    retryable: false,
    next_action: "select",
    doi: null,
    abstract: "A paper about traceable research evidence.",
    published_at: null,
    source_updated_at: null,
    source_url: "https://example.test/paper",
    pdf_url: null,
    pdf_urls: [],
    is_open_access: false,
    license: null,
    source_links: ["https://example.test/paper"],
    discovery_query: "traceable evidence",
    discovered_at: "2026-07-13T00:00:00Z",
    dismissed: false,
    ...overrides,
  };
}

function workspace(papers: ReturnType<typeof paper>[], operations: unknown[] = [], outline: unknown = null) {
  return {
    id: workspaceId,
    topic: "Traceable research evidence",
    report_language: "zh",
    state: papers.some((item) => item.selected) ? "active" : "setup",
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
    papers,
    operations,
    outline,
  };
}

test("researcher can discover, authorise, process, and remove a paper in the browser", async ({ page }) => {
  let created = false;
  let discovered = false;
  let uploaded = false;
  let currentPaper = paper();
  let currentOperation = null as Record<string, unknown> | null;
  let currentOutline = null as Record<string, unknown> | null;

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (request.method() === "GET" && path === "/api/workspaces") {
      await route.fulfill({ json: created ? [workspace([currentPaper], currentOperation ? [currentOperation] : [], currentOutline)] : [] });
      return;
    }
    if (request.method() === "POST" && path === "/api/workspaces") {
      created = true;
      await route.fulfill({ status: 201, json: workspace([]) });
      return;
    }
    if (request.method() === "GET" && path === `/api/workspaces/${workspaceId}`) {
      await route.fulfill({ json: workspace(discovered ? [currentPaper] : [], currentOperation ? [currentOperation] : [], currentOutline) });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/papers/discover`) {
      discovered = true;
      await route.fulfill({
        json: {
          provider: "openalex",
          query: "traceable evidence",
          status: "succeeded",
          candidates: [currentPaper],
          page: 1,
          per_page: 10,
          total_count: 1,
          next_page: null,
          error_message: null,
          retryable: false,
          retry_after_seconds: null,
          next_action: null,
        },
      });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/papers/${candidateId}/import`) {
      currentPaper = paper({ selected: true, evidence_readiness: "awaiting_authorised_file", next_action: "upload_authorised_pdf" });
      await route.fulfill({ json: { paper: currentPaper, operation: null } });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/papers/upload`) {
      uploaded = true;
      currentPaper = paper({ selected: true, evidence_readiness: "ready", evidence_eligible: true, active_document_version_id: "version-1", next_action: null });
      currentOperation = {
        id: operationId,
        workspace_id: workspaceId,
        paper_id: candidateId,
        operation_type: "import_authorised_paper",
        status: "succeeded",
        phase: "ready",
        error_category: null,
        error_message: null,
        retry_action: null,
        completed_work: 1,
        total_work: 1,
        started_at: "2026-07-13T00:00:00Z",
        finished_at: "2026-07-13T00:00:01Z",
      };
      await route.fulfill({ status: 202, json: { paper: currentPaper, operation: currentOperation } });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/outline/generate`) {
      currentOutline = {
        id: "outline-1",
        workspace_id: workspaceId,
        revision_number: 1,
        status: "draft",
        title: "Traceable research evidence review",
        research_question: "How can research evidence remain traceable?",
        sections: [
          { id: "research-question", title: "Research question and scope", description: "Scope" },
          { id: "methods-findings", title: "Methods and findings", description: "Findings" },
        ],
        evidence_paper_ids: [candidateId],
        created_at: "2026-07-13T00:00:00Z",
        updated_at: "2026-07-13T00:00:00Z",
        approved_at: null,
      };
      currentOperation = {
        id: "outline-operation-1",
        workspace_id: workspaceId,
        paper_id: null,
        operation_type: "generate_outline",
        status: "succeeded",
        phase: "draft_ready",
        error_category: null,
        error_message: null,
        retry_action: null,
        completed_work: 1,
        total_work: 1,
        started_at: "2026-07-13T00:00:00Z",
        finished_at: "2026-07-13T00:00:01Z",
      };
      await route.fulfill({ status: 202, json: currentOperation });
      return;
    }
    if (request.method() === "PUT" && path === `/api/workspaces/${workspaceId}/outline`) {
      const body = JSON.parse(request.postData() || "{}");
      const approvedEdit = currentOutline?.status === "approved";
      currentOutline = { ...currentOutline, ...body, id: approvedEdit ? "outline-2" : "outline-1", status: "draft", revision_number: approvedEdit ? 2 : 1, updated_at: "2026-07-13T00:00:01Z" };
      await route.fulfill({ json: currentOutline });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/outline/approve`) {
      currentOutline = { ...currentOutline, status: "approved", approved_at: "2026-07-13T00:00:02Z" };
      await route.fulfill({ json: currentOutline });
      return;
    }
    if (request.method() === "GET" && path === `/api/workspaces/${workspaceId}/outline/revisions`) {
      await route.fulfill({ json: [currentOutline, { ...currentOutline, id: "outline-history-1", revision_number: 1, status: "approved", title: "Earlier approved outline" }] });
      return;
    }
    if (request.method() === "POST" && path.startsWith(`/api/workspaces/${workspaceId}/outline/revisions/`) && path.endsWith("/restore")) {
      currentOutline = { ...currentOutline, id: "outline-restored", revision_number: 3, status: "draft", title: "Earlier approved outline" };
      await route.fulfill({ json: currentOutline });
      return;
    }
    if (request.method() === "DELETE" && path === `/api/workspaces/${workspaceId}/papers/${candidateId}`) {
      currentPaper = paper({ selected: false, evidence_readiness: uploaded ? "ready" : "unavailable", evidence_eligible: false });
      await route.fulfill({ json: currentPaper });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/papers/${candidateId}/dismiss`) {
      currentPaper = paper({ selected: false, dismissed: true });
      await route.fulfill({ json: currentPaper });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/papers/${candidateId}/restore`) {
      currentPaper = paper({ selected: false, dismissed: false });
      await route.fulfill({ json: currentPaper });
      return;
    }
    if (request.method() === "GET" && path === `/api/operations/${operationId}`) {
      await route.fulfill({ json: currentOperation });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: "not mocked" } });
  });

  await page.goto("/");
  await page.getByTestId("workspace-topic").fill("Traceable research evidence");
  await page.getByTestId("workspace-create").click();
  await expect(page.getByTestId("workspace-select")).toHaveValue(workspaceId);

  const desktopPanelStyles = await page.locator(".panel").evaluateAll((panels) => panels.map((panel) => {
    const style = getComputedStyle(panel);
    return { overflowY: style.overflowY, scrollbarGutter: style.scrollbarGutter, maxHeight: style.maxHeight };
  }));
  expect(desktopPanelStyles).toHaveLength(3);
  expect(desktopPanelStyles).toEqual(expect.arrayContaining([
    expect.objectContaining({ overflowY: "auto", scrollbarGutter: "stable" }),
  ]));
  await expect(page.locator(".panel-heading").first()).toHaveCSS("position", "sticky");

  await page.getByTestId("discovery-query").fill("traceable evidence");
  await page.getByTestId("discovery-submit").click();
  await expect(page.getByTestId("paper-candidate")).toBeVisible();

  await page.getByTestId(`import-paper-${candidateId}`).click();
  await expect(page.getByTestId(`authorised-upload-${candidateId}`)).toBeAttached();
  await page.getByTestId(`authorised-upload-${candidateId}`).setInputFiles({
    name: "authorised-paper.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-authorised"),
  });
  await page.getByRole("button", { name: "上传授权文件" }).click();
  await expect(page.getByTestId("paper-evidence-eligible")).toBeVisible();
  await page.getByTestId("outline-generate").click();
  await expect(page.getByTestId("outline-research-question")).toHaveValue("How can research evidence remain traceable?");
  await page.getByTestId("outline-research-question").fill("How can selected evidence remain traceable?");
  await page.getByTestId("outline-add-section").click();
  await page.getByTestId("outline-save").click();
  await page.getByTestId("outline-approve").click();
  await expect(page.getByTestId("outline-status")).toContainText("已审批");
  await page.getByTestId("outline-research-question").fill("An edited approved question");
  await page.getByTestId("outline-save").click();
  await expect(page.getByTestId("outline-status")).toContainText("草稿");
  await page.getByTestId("outline-history").click();
  await expect(page.getByTestId("outline-history-panel")).toBeVisible();
  await page.getByRole("button", { name: "恢复为新草稿" }).click();
  await expect(page.getByTestId("outline-status")).toContainText("草稿");
  await page.reload();
  await expect(page.getByTestId("outline-status")).toContainText("草稿");
  await expect(page.getByTestId("operation-status")).toContainText("已完成");

  await page.getByTestId(`remove-paper-${candidateId}`).click();
  await expect(page.getByTestId("paper-candidate")).toBeVisible();
  await page.getByTestId(`dismiss-paper-${candidateId}`).click();
  await expect(page.getByTestId("paper-candidate")).toHaveCount(0);
  await page.getByTestId(`restore-paper-${candidateId}`).click();
  await expect(page.getByTestId("paper-candidate")).toBeVisible();

  currentPaper = paper({
    selected: true,
    evidence_readiness: "failed",
    retryable: true,
    failure_message: "All public PDF sources failed: The selected public URL did not return a PDF.",
  });
  await page.reload();
  await expect(page.getByTestId("paper-selected")).toContainText("所有公开 PDF 来源均失败");
  await expect(page.getByTestId(`authorised-upload-${candidateId}`)).toBeAttached();

  await page.setViewportSize({ width: 640, height: 800 });
  const mobilePanelStyles = await page.locator(".panel").evaluateAll((panels) => panels.map((panel) => {
    const style = getComputedStyle(panel);
    return { overflowY: style.overflowY, maxHeight: style.maxHeight };
  }));
  expect(mobilePanelStyles).toEqual(expect.arrayContaining([
    expect.objectContaining({ overflowY: "visible", maxHeight: "none" }),
  ]));
});
