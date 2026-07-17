import { expect, test } from "@playwright/test";

const workspaceId = "workspace-1";
const candidateId = "candidate-1";

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

function workspaceRecord() {
  return {
    id: workspaceId,
    topic: "Traceable research evidence",
    report_language: "zh",
    state: "active",
    created_at: "2026-07-13T00:00:00Z",
    updated_at: "2026-07-13T00:00:00Z",
    papers: [],
    operations: [],
    outline: null,
    report: null,
  };
}

test("researcher can prepare papers, recover import gaps, and read the authorised original PDF", async ({ page }) => {
  let created = false;
  let discovered = false;
  let pdfAvailable = true;
  let currentPaper = paper();
  let operations: Array<Record<string, unknown>> = [];

  const viewState = () => {
    const selectedPapers = currentPaper.selected ? [currentPaper] : [];
    const readyPapers = currentPaper.evidence_eligible ? [currentPaper] : [];
    const candidatePapers = discovered && !currentPaper.selected && !currentPaper.dismissed ? [currentPaper] : [];
    const dismissedPapers = currentPaper.dismissed ? [currentPaper] : [];
    const outlineApproved = false;

    return {
      workspace: {
        id: workspaceId,
        topic: "Traceable research evidence",
        report_language: "zh",
        state: selectedPapers.length ? "active" : "setup",
        created_at: "2026-07-13T00:00:00Z",
        updated_at: "2026-07-13T00:00:00Z",
      },
      stages: [
        {
          key: "import",
          title: "Literature Import",
          available: true,
          detail: "Discover Candidate Papers, upload authorised PDFs, and move Selected Papers to evidence-ready status.",
          next_action_stage: null,
          next_action_label: null,
        },
        {
          key: "reading",
          title: "Paper Reading",
          available: readyPapers.length > 0,
          detail: readyPapers.length
            ? "Read any evidence-ready Selected Paper in its authorised original PDF."
            : "No Selected Paper is evidence-ready yet. Prepare at least one paper in Literature Import first.",
          next_action_stage: readyPapers.length ? null : "import",
          next_action_label: readyPapers.length ? null : "Go to Literature Import",
        },
        {
          key: "outline",
          title: "Report Outline",
          available: readyPapers.length > 0,
          detail: readyPapers.length
            ? "Generate and edit the report outline from evidence-ready Selected Papers."
            : "A Report Outline needs at least one evidence-ready Selected Paper.",
          next_action_stage: readyPapers.length ? null : "import",
          next_action_label: readyPapers.length ? null : "Prepare Papers",
        },
        {
          key: "writing",
          title: "Report Writing",
          available: outlineApproved && readyPapers.length > 0,
          detail: "Report writing becomes available after at least one paper is ready and the current outline is approved.",
          next_action_stage: readyPapers.length ? "outline" : "import",
          next_action_label: readyPapers.length ? "Approve the Outline" : "Prepare Papers",
        },
      ],
      import_state: {
        selected_papers: selectedPapers,
        ready_papers: readyPapers,
        candidate_papers: candidatePapers,
        dismissed_papers: dismissedPapers,
        operations,
      },
      reading_state: {
        active_paper_id: readyPapers[0]?.id ?? selectedPapers[0]?.id ?? null,
        active_paper: readyPapers[0] ?? selectedPapers[0] ?? null,
        ready_papers: readyPapers,
        pdf_available: readyPapers.length > 0 && pdfAvailable,
        pdf_url: readyPapers.length > 0 && pdfAvailable ? `/api/workspaces/${workspaceId}/papers/${candidateId}/pdf` : null,
        unavailable_reason: readyPapers.length > 0 && !pdfAvailable
          ? "The authorised original PDF for this paper is unavailable. Historical metadata remains visible, but the workspace will not reconstruct a reader from chunks."
          : selectedPapers.length > 0 && !readyPapers.length
            ? "This Selected Paper is not evidence-ready yet. Finish import, parsing, and indexing first."
            : null,
      },
      outline: null,
      report: null,
    };
  };

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (request.method() === "GET" && path === "/api/workspaces") {
      await route.fulfill({ json: created ? [workspaceRecord()] : [] });
      return;
    }
    if (request.method() === "POST" && path === "/api/workspaces") {
      created = true;
      await route.fulfill({ status: 201, json: workspaceRecord() });
      return;
    }
    if (request.method() === "GET" && path === `/api/workspaces/${workspaceId}/view`) {
      await route.fulfill({ json: viewState() });
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
      await route.fulfill({ status: 202, json: { paper: currentPaper, operation: null } });
      return;
    }
    if (request.method() === "POST" && path === `/api/workspaces/${workspaceId}/papers/upload`) {
      currentPaper = paper({
        selected: true,
        evidence_readiness: "ready",
        evidence_eligible: true,
        active_document_version_id: "version-1",
        next_action: null,
      });
      operations = [
        {
          id: "operation-1",
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
        },
      ];
      await route.fulfill({ status: 202, json: { paper: currentPaper, operation: operations[0] } });
      return;
    }
    if (request.method() === "DELETE" && path === `/api/workspaces/${workspaceId}/papers/${candidateId}`) {
      currentPaper = paper({ selected: false, evidence_readiness: "ready", evidence_eligible: false, active_document_version_id: null });
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
    if (request.method() === "GET" && path === `/api/workspaces/${workspaceId}/papers/${candidateId}/pdf`) {
      if (!pdfAvailable) {
        await route.fulfill({ status: 404, json: { error: "paper_pdf_unavailable" } });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: Buffer.from("%PDF-1.4 mocked"),
      });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: "not mocked" } });
  });

  await page.goto("/");
  await page.getByTestId("workspace-topic").fill("Traceable research evidence");
  await page.getByTestId("workspace-create").click();
  await expect(page.getByTestId("workspace-select")).toHaveValue(workspaceId);

  await expect(page.getByTestId("stage-import")).toBeVisible();
  await expect(page.getByTestId("stage-reading")).toBeVisible();
  await expect(page.getByTestId("stage-outline")).toBeVisible();
  await expect(page.getByTestId("stage-writing")).toBeVisible();

  await page.getByTestId("stage-reading").click();
  await expect(page.getByText("This stage is not ready yet.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Go to Literature Import" }).first()).toBeVisible();

  await page.getByTestId("stage-import").click();
  await page.getByTestId("discovery-query").fill("traceable evidence");
  await page.getByTestId("discovery-submit").click();
  await expect(page.getByTestId("paper-candidate")).toBeVisible();

  await page.getByTestId(`import-paper-${candidateId}`).click();
  await page.getByTestId(`authorised-upload-${candidateId}`).setInputFiles({
    name: "authorised-paper.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-authorised"),
  });
  await page.getByRole("button", { name: "Upload authorised PDF" }).click();

  await expect(page.getByTestId(`ready-paper-row-${candidateId}`)).toBeVisible();
  await page.getByTestId(`ready-paper-row-${candidateId}`).click();
  await expect(page.getByTestId("paper-reading-frame")).toHaveAttribute("src", `/api/workspaces/${workspaceId}/papers/${candidateId}/pdf`);

  await page.getByTestId("stage-writing").click();
  await expect(
    page.getByText("Report writing becomes available after at least one paper is ready and the current outline is approved.").first(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve the Outline" }).first()).toBeVisible();

  pdfAvailable = false;
  await page.reload();
  await page.getByTestId("stage-reading").click();
  await expect(page.getByText("Original PDF unavailable")).toBeVisible();
  await expect(page.getByText("will not reconstruct a reader from chunks")).toBeVisible();

  await page.getByTestId("stage-import").click();
  await page.getByTestId(`remove-paper-${candidateId}`).click();
  await expect(page.getByTestId("paper-candidate")).toBeVisible();
  await page.getByTestId(`dismiss-paper-${candidateId}`).click();
  await expect(page.getByTestId("paper-candidate")).toHaveCount(0);
  const restoreButton = page.getByTestId(`restore-paper-${candidateId}`);
  await restoreButton.scrollIntoViewIfNeeded();
  await restoreButton.click();
  await expect(page.getByTestId("paper-candidate")).toBeVisible();
});
