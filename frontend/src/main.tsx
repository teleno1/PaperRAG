import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  ApiRequestError,
  approveOutline,
  createWorkspace,
  discoverPapers,
  dismissPaper,
  generateOutline,
  generateReport,
  getWorkspaceView,
  importPaper,
  listOutlineRevisions,
  listWorkspaces,
  removePaper,
  restoreOutlineRevision,
  restorePaper,
  retryOperation,
  retryPaper,
  saveOutline,
  saveReportDraft,
  selectPaper,
  uploadPaper,
} from "./api";
import type {
  DiscoveryResponse,
  EvidenceReadiness,
  LiteratureReport,
  ReportLanguage,
  ReportOutline,
  ResearchPaper,
  ResearchWorkspace,
  WorkspaceOperation,
  WorkspaceStageKey,
  WorkspaceStageState,
  WorkspaceViewState,
} from "./types";
import "./styles.css";

const stageOrder: WorkspaceStageKey[] = ["import", "reading", "outline", "writing"];

const readinessLabels: Record<EvidenceReadiness, string> = {
  awaiting_authorised_file: "Awaiting authorised PDF",
  importing: "Importing",
  parsing: "Parsing",
  indexing: "Indexing",
  ready: "Ready",
  failed: "Failed",
  unavailable: "Unavailable",
};

const operationLabels: Record<string, string> = {
  import_paper: "Upload paper",
  import_authorised_paper: "Upload authorised PDF",
  import_discovered_paper: "Import discovered paper",
  retry_paper_import: "Retry paper preparation",
  generate_outline: "Generate outline",
  generate_report: "Generate report",
  rebuild_evidence_index: "Rebuild evidence index",
};

const operationStatusLabels: Record<WorkspaceOperation["status"], string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  interrupted: "Interrupted",
  cancelled: "Cancelled",
};

const phaseLabels: Record<string, string> = {
  importing: "Importing",
  parsing: "Parsing",
  indexing: "Indexing",
  ready: "Ready",
  generating: "Generating",
  draft_ready: "Draft ready",
  report_ready: "Report ready",
  interrupted: "Interrupted",
};

function localizeError(reason: unknown): string {
  if (reason instanceof ApiRequestError) {
    if (reason.code === "provider_rate_limited") {
      return reason.nextAction === "configure_openalex_api_key"
        ? "OpenAlex requires an API key in this environment. Configure OPENALEX_API_KEY or switch to arXiv."
        : "OpenAlex is rate limited right now. Retry after the reset window or switch to arXiv.";
    }
    if (reason.code === "provider_auth_required") {
      return "OpenAlex requires an API key in this environment. Configure OPENALEX_API_KEY or switch to arXiv.";
    }
    if (reason.code === "outline_not_found") return "There is no saved outline yet for this workspace.";
    if (reason.code === "outline_unavailable") return "Prepare at least one Selected Paper until it is evidence-ready before generating the outline.";
    if (reason.code === "invalid_outline") return "The current outline changed. Refresh the workspace view and try again.";
    if (reason.code === "report_unavailable") {
      return reason.nextAction === "confirm_ready_subset"
        ? "Some Selected Papers are not ready. Confirm the ready subset before generating the report."
        : "Report generation needs an approved outline and at least one evidence-ready Selected Paper.";
    }
    if (reason.code === "invalid_report") return "The current report draft changed. Refresh the workspace view and try again.";
    if (reason.code === "paper_not_found") return "That paper is no longer available in the current workspace.";
    return reason.message;
  }
  return "The request failed. Check the workspace service and try again.";
}

function paperFailureMessage(paper: ResearchPaper): string | null {
  if (paper.evidence_readiness === "awaiting_authorised_file") {
    return "No open-access PDF could be imported automatically. Upload an authorised original PDF to continue.";
  }
  if (paper.evidence_readiness === "failed") {
    return paper.failure_message || "Preparation failed. Retry the paper or upload another authorised PDF.";
  }
  return null;
}

function operationErrorMessage(operation: WorkspaceOperation): string | null {
  if (!operation.error_message) return null;
  return operation.error_message;
}

function App() {
  const [workspaces, setWorkspaces] = useState<ResearchWorkspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [viewState, setViewState] = useState<WorkspaceViewState | null>(null);
  const [activeStage, setActiveStage] = useState<WorkspaceStageKey>("import");
  const [activeReadingPaperId, setActiveReadingPaperId] = useState<string | null>(null);
  const [discovery, setDiscovery] = useState<DiscoveryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [newLanguage, setNewLanguage] = useState<ReportLanguage>("zh");
  const [newTopic, setNewTopic] = useState("");
  const [discoveryQuery, setDiscoveryQuery] = useState("");
  const [provider, setProvider] = useState<"openalex" | "arxiv">("openalex");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [candidateFiles, setCandidateFiles] = useState<Record<string, File | null>>({});
  const [outlineDraft, setOutlineDraft] = useState<ReportOutline | null>(null);
  const [outlineHistory, setOutlineHistory] = useState<ReportOutline[] | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [reportDraft, setReportDraft] = useState<LiteratureReport | null>(null);
  const [reportDirty, setReportDirty] = useState(false);

  const refreshWorkspaces = useCallback(async () => {
    const result = await listWorkspaces();
    setWorkspaces(result);
    if (!workspaceId && result[0]) setWorkspaceId(result[0].id);
  }, [workspaceId]);

  const refreshView = useCallback(async (id: string, readingPaperId?: string | null) => {
    const result = await getWorkspaceView(id, readingPaperId);
    setViewState(result);
    setDiscoveryQuery((current) => current || result.workspace.topic);
    setActiveReadingPaperId(result.reading_state.active_paper_id ?? null);
    setWorkspaces((current) => current.map((item) => (item.id === id ? { ...item, ...result.workspace } : item)));
  }, []);

  useEffect(() => {
    void refreshWorkspaces().catch((reason: unknown) => setError(localizeError(reason)));
  }, [refreshWorkspaces]);

  useEffect(() => {
    if (!workspaceId) {
      setViewState(null);
      return;
    }
    void refreshView(workspaceId, activeReadingPaperId).catch((reason: unknown) => setError(localizeError(reason)));
  }, [activeReadingPaperId, refreshView, workspaceId]);

  useEffect(() => {
    setActiveStage("import");
    setDiscovery(null);
    setOutlineHistory(null);
    setHistoryOpen(false);
  }, [workspaceId]);

  useEffect(() => {
    const outline = viewState?.outline;
    if (!outline) {
      setOutlineDraft(null);
      return;
    }
    setOutlineDraft((current) => {
      if (current && current.id === outline.id && current.updated_at === outline.updated_at && current.status === outline.status) {
        return current;
      }
      return { ...outline, sections: outline.sections.map((section) => ({ ...section })) };
    });
  }, [viewState?.outline]);

  useEffect(() => {
    const report = viewState?.report;
    if (!report) {
      if (!reportDirty) setReportDraft(null);
      return;
    }
    if (reportDirty) return;
    setReportDraft({
      ...report,
      sections: report.sections.map((section) => ({
        ...section,
        claims: section.claims.map((claim) => ({
          ...claim,
          citations: claim.citations.map((citation) => ({ ...citation })),
        })),
      })),
    });
  }, [reportDirty, viewState?.report]);

  const operations = viewState?.import_state.operations ?? [];
  const selectedPapers = viewState?.import_state.selected_papers ?? [];
  const readyPapers = viewState?.import_state.ready_papers ?? [];
  const candidatePapers = viewState?.import_state.candidate_papers ?? [];
  const dismissedPapers = viewState?.import_state.dismissed_papers ?? [];
  const selectedNotReady = selectedPapers.filter((paper) => !paper.evidence_eligible);
  const readyCount = readyPapers.length;
  const activeOperation = operations.some((operation) => operation.status === "queued" || operation.status === "running");
  const outlineGenerating = operations.some(
    (operation) => operation.operation_type === "generate_outline" && (operation.status === "queued" || operation.status === "running"),
  );
  const reportGenerating = operations.some(
    (operation) => operation.operation_type === "generate_report" && (operation.status === "queued" || operation.status === "running"),
  );

  useEffect(() => {
    if (!workspaceId || !activeOperation) return undefined;
    const timer = window.setInterval(() => {
      void refreshView(workspaceId, activeReadingPaperId).catch((reason: unknown) => setError(localizeError(reason)));
    }, 800);
    return () => window.clearInterval(timer);
  }, [activeOperation, activeReadingPaperId, refreshView, workspaceId]);

  useEffect(() => {
    if (!reportDirty || !reportDraft || !workspaceId) return undefined;
    const timer = window.setTimeout(() => {
      void saveReportDraft(workspaceId, reportDraft)
        .then((saved) => {
          setReportDraft(saved);
          setReportDirty(false);
          setViewState((current) => current ? { ...current, report: saved } : current);
        })
        .catch((reason: unknown) => setError(localizeError(reason)));
    }, 500);
    return () => window.clearTimeout(timer);
  }, [reportDirty, reportDraft, workspaceId]);

  const stageMap = useMemo(() => new Map((viewState?.stages ?? []).map((stage) => [stage.key, stage])), [viewState?.stages]);
  const currentStage = stageMap.get(activeStage) ?? defaultStage(activeStage);

  async function runAction(key: string, action: () => Promise<void>, readingPaperId?: string | null) {
    setBusyKey(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      if (workspaceId) await refreshView(workspaceId, readingPaperId ?? activeReadingPaperId);
    } catch (reason: unknown) {
      setError(localizeError(reason));
    } finally {
      setBusyKey(null);
    }
  }

  function addOperation(operation: WorkspaceOperation | null) {
    if (!operation) return;
    setViewState((current) => {
      if (!current) return current;
      return {
        ...current,
        import_state: {
          ...current.import_state,
          operations: [operation, ...current.import_state.operations.filter((item) => item.id !== operation.id)],
        },
      };
    });
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newTopic.trim()) return;
    await runAction("create-workspace", async () => {
      const result = await createWorkspace(newTopic, newLanguage);
      setNewTopic("");
      setWorkspaceId(result.id);
      setWorkspaces((current) => [...current, result]);
      setDiscoveryQuery(result.topic);
      setNotice("Workspace created. Start by uploading or discovering papers for the evidence boundary.");
    });
  }

  async function handleDiscover(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || !discoveryQuery.trim()) return;
    await runAction("discover", async () => {
      const result = await discoverPapers(workspaceId, discoveryQuery, provider);
      setDiscovery(result);
      if (result.status === "succeeded") {
        setNotice(`Stored ${result.candidates.length} Candidate Papers. They will not become evidence until you select and prepare them.`);
      } else if (result.status === "empty") {
        setNotice("No new Candidate Papers were found for this query.");
      } else if (result.provider === "openalex" && result.next_action === "configure_openalex_api_key") {
        setError("OpenAlex requires an API key in this environment. Configure OPENALEX_API_KEY or switch to arXiv.");
      } else if (result.provider === "openalex" && result.retry_after_seconds) {
        setError(`OpenAlex is rate limited. Retry in about ${result.retry_after_seconds} seconds or switch to arXiv.`);
      } else {
        setError("Paper discovery failed for now. Retry later or switch providers.");
      }
    });
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>, candidateId?: string) {
    event.preventDefault();
    if (!workspaceId) return;
    const file = candidateId ? candidateFiles[candidateId] : uploadFile;
    if (!file) return;
    await runAction(candidateId ? `upload-${candidateId}` : "upload-paper", async () => {
      const result = await uploadPaper(workspaceId, file, candidateId);
      addOperation(result.operation);
      if (candidateId) setCandidateFiles((current) => ({ ...current, [candidateId]: null }));
      else setUploadFile(null);
      setNotice("The authorised PDF was accepted and paper preparation is now running in the background.");
    });
  }

  async function handleImport(paper: ResearchPaper) {
    if (!workspaceId) return;
    await runAction(`import-${paper.id}`, async () => {
      const result = await importPaper(workspaceId, paper.id);
      addOperation(result.operation);
      setNotice(
        result.operation
          ? "Open-access PDF import started. The paper is now in the Selected Paper set."
          : "No open-access PDF was available automatically. Upload an authorised PDF instead.",
      );
    });
  }

  async function handleRetry(paper: ResearchPaper) {
    if (!workspaceId) return;
    await runAction(`retry-${paper.id}`, async () => {
      const result = await retryPaper(workspaceId, paper.id);
      addOperation(result.operation);
      setNotice("A new paper-preparation attempt has been created. Earlier failure history remains intact.");
    });
  }

  async function handleDismiss(paper: ResearchPaper) {
    if (!workspaceId) return;
    await runAction(`dismiss-${paper.id}`, async () => {
      await dismissPaper(workspaceId, paper.id);
      setNotice("The Candidate Paper was hidden from the current candidate set. You can restore it later.");
    });
  }

  async function handleRestorePaper(paper: ResearchPaper) {
    if (!workspaceId) return;
    await runAction(`restore-${paper.id}`, async () => {
      await restorePaper(workspaceId, paper.id);
      setNotice("The Candidate Paper was restored to the visible discovery set.");
    });
  }

  async function handleChooseReadingPaper(paperId: string) {
    if (!workspaceId) return;
    setActiveReadingPaperId(paperId);
    await refreshView(workspaceId, paperId).catch((reason: unknown) => setError(localizeError(reason)));
  }

  async function handleGenerateOutline() {
    if (!workspaceId) return;
    await runAction("generate-outline", async () => {
      const operation = await generateOutline(workspaceId);
      addOperation(operation);
      setNotice("Outline generation is queued. When it completes, you can edit and approve the new draft.");
    });
  }

  async function handleGenerateReport() {
    if (!workspaceId) return;
    const useReadySubset = readyCount < selectedPapers.length;
    await runAction("generate-report", async () => {
      const operation = await generateReport(workspaceId, useReadySubset);
      addOperation(operation);
      setNotice(
        useReadySubset
          ? "Report generation will use only the evidence-ready Selected Papers from this workspace."
          : "Report generation is queued and will publish a new editable draft when it succeeds.",
      );
    });
  }

  async function handleSaveReport() {
    if (!workspaceId || !reportDraft) return;
    await runAction("save-report", async () => {
      const saved = await saveReportDraft(workspaceId, reportDraft);
      setReportDraft(saved);
      setReportDirty(false);
      setNotice("The current report draft was saved without rewriting its existing evidence history.");
    });
  }

  async function handleRetryOutline(operation: WorkspaceOperation) {
    await runAction(`retry-${operation.id}`, async () => {
      const retry = await retryOperation(operation.id);
      addOperation(retry);
      setNotice("Outline generation was queued again from its persisted operation state.");
    });
  }

  async function handleRetryReport(operation: WorkspaceOperation) {
    await runAction(`retry-${operation.id}`, async () => {
      const retry = await retryOperation(operation.id);
      addOperation(retry);
      setNotice("Report generation was queued again. The current published draft remains unchanged until the retry succeeds.");
    });
  }

  async function handleRetryIndex(operation: WorkspaceOperation) {
    await runAction(`retry-${operation.id}`, async () => {
      const retry = await retryOperation(operation.id);
      addOperation(retry);
      setNotice("The evidence index rebuild was queued again from the persisted workspace operation.");
    });
  }

  async function handleSaveOutline() {
    if (!workspaceId || !outlineDraft) return;
    await runAction("save-outline", async () => {
      await saveOutline(workspaceId, outlineDraft);
      setNotice("The outline draft was saved. Approved history remains traceable.");
    });
  }

  async function handleApproveOutline() {
    if (!workspaceId || !outlineDraft) return;
    await runAction("approve-outline", async () => {
      await approveOutline(workspaceId, outlineDraft.id);
      setNotice("The current outline revision is now approved for downstream report generation.");
    });
  }

  async function handleOpenHistory() {
    if (!workspaceId) return;
    await runAction("outline-history", async () => {
      const revisions = await listOutlineRevisions(workspaceId);
      setOutlineHistory(revisions);
      setHistoryOpen(true);
    });
  }

  async function handleRestoreOutline(revision: ReportOutline) {
    if (!workspaceId) return;
    await runAction(`restore-outline-${revision.id}`, async () => {
      const restored = await restoreOutlineRevision(workspaceId, revision.id);
      setOutlineDraft({ ...restored, sections: restored.sections.map((section) => ({ ...section })) });
      setHistoryOpen(false);
      setOutlineHistory(null);
      setNotice(`Created a new outline draft from revision ${revision.revision_number}.`);
    });
  }

  function updateOutlineDraft(update: (outline: ReportOutline) => ReportOutline) {
    setOutlineDraft((current) => (current ? update(current) : current));
  }

  function addOutlineSection() {
    updateOutlineDraft((current) => ({
      ...current,
      sections: [...current.sections, { id: `section-${Date.now()}`, title: "New section", description: "" }],
    }));
  }

  function moveOutlineSection(index: number, offset: -1 | 1) {
    updateOutlineDraft((current) => {
      const target = index + offset;
      if (target < 0 || target >= current.sections.length) return current;
      const sections = [...current.sections];
      [sections[index], sections[target]] = [sections[target], sections[index]];
      return { ...current, sections };
    });
  }

  function updateReportDraft(update: (report: LiteratureReport) => LiteratureReport) {
    setReportDraft((current) => (current ? update(current) : current));
    setReportDirty(true);
  }

  if (!viewState && !workspaces.length) {
    return (
      <div className="empty-shell">
        <div className="empty-card">
          <p className="eyebrow">PaperRAG</p>
          <h1>Read papers, then write a traceable literature report.</h1>
          <p className="muted">
            Start a Research Workspace with one topic. Candidate Papers stay outside the evidence boundary until you
            explicitly select and prepare them.
          </p>
          <WorkspaceForm
            topic={newTopic}
            language={newLanguage}
            submitLabel="Create your first workspace"
            onTopicChange={setNewTopic}
            onLanguageChange={setNewLanguage}
            onSubmit={handleCreate}
            busy={busyKey === "create-workspace"}
          />
          {error && <StatusBanner tone="danger" text={error} />}
        </div>
      </div>
    );
  }

  if (!viewState) {
    return <div className="loading-shell">Loading workspace...</div>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">PaperRAG</p>
          <h1>{viewState.workspace.topic}</h1>
          <p className="topbar-subtitle">
            Report language: {viewState.workspace.report_language === "zh" ? "Chinese" : "English"}.
          </p>
        </div>
        <div className="workspace-switcher">
          <label htmlFor="workspace-select">Workspace</label>
          <select id="workspace-select" data-testid="workspace-select" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)}>
            {workspaces.map((item) => (
              <option value={item.id} key={item.id}>
                {item.topic}
              </option>
            ))}
          </select>
        </div>
      </header>

      <main className="workspace-shell">
        <aside className="workspace-column stage-column">
          <div className="scroll-pane">
            <SectionLabel label="Workflow Stages" detail="Accepted desktop workspace" />
            <nav className="stage-nav">
              {stageOrder.map((stageKey, index) => {
                const stage = stageMap.get(stageKey) ?? defaultStage(stageKey);
                return (
                  <button
                    key={stage.key}
                    type="button"
                    className={activeStage === stage.key ? "stage-button stage-button-active" : "stage-button"}
                    data-testid={`stage-${stage.key}`}
                    onClick={() => setActiveStage(stage.key)}
                  >
                    <span className="stage-index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="stage-copy">
                      <strong>{stage.title}</strong>
                      <small>{stage.available ? "Available" : "Needs a prerequisite"}</small>
                    </span>
                  </button>
                );
              })}
            </nav>
            <div className="stage-summary">
              <strong>{readyCount}</strong>
              <span>evidence-ready papers</span>
              <small>
                Selected: {selectedPapers.length} | Candidates: {candidatePapers.length}
              </small>
            </div>
            <div className="new-workspace-block">
              <SectionLabel label="New Workspace" detail="Single-user deployment" />
              <WorkspaceForm
                compact
                topic={newTopic}
                language={newLanguage}
                submitLabel="Create"
                onTopicChange={setNewTopic}
                onLanguageChange={setNewLanguage}
                onSubmit={handleCreate}
                busy={busyKey === "create-workspace"}
              />
            </div>
          </div>
        </aside>

        <section className="workspace-column surface-column">
          <div className="scroll-pane">
            <StageHeader stage={currentStage} />
            {notice && <StatusBanner tone="success" text={notice} />}
            {error && <StatusBanner tone="danger" text={error} />}

            {activeStage === "import" && (
              <ImportStage
                workspace={viewState.workspace}
                discovery={discovery}
                discoveryQuery={discoveryQuery}
                provider={provider}
                uploadFile={uploadFile}
                busyKey={busyKey}
                candidateFiles={candidateFiles}
                candidatePapers={candidatePapers}
                onDiscoveryQueryChange={setDiscoveryQuery}
                onProviderChange={setProvider}
                onUploadFileChange={setUploadFile}
                onDiscover={handleDiscover}
                onUpload={handleUpload}
                onImport={(paper) => void handleImport(paper)}
                onSelect={(paper) => void runAction(`select-${paper.id}`, async () => {
                  if (!workspaceId) return;
                  await selectPaper(workspaceId, paper.id);
                  setNotice("The paper moved into the Selected Paper boundary. It still needs preparation before it can become evidence.");
                })}
                onDismiss={(paper) => void handleDismiss(paper)}
                onCandidateFileChange={(paperId, file) => setCandidateFiles((current) => ({ ...current, [paperId]: file }))}
                onCandidateUpload={(paperId, event) => void handleUpload(event, paperId)}
              />
            )}

            {activeStage === "reading" && (
              <ReadingStage
                stage={currentStage}
                readingState={viewState.reading_state}
                onStageAction={(stageKey) => setActiveStage(stageKey)}
              />
            )}

            {activeStage === "outline" && (
              <OutlineStage
                stage={currentStage}
                outline={outlineDraft}
                readyCount={readyCount}
                generating={outlineGenerating}
                busyKey={busyKey}
                onGenerate={() => void handleGenerateOutline()}
                onSave={() => void handleSaveOutline()}
                onApprove={() => void handleApproveOutline()}
                onChange={updateOutlineDraft}
                onAddSection={addOutlineSection}
                onMoveSection={moveOutlineSection}
                onOpenHistory={() => void handleOpenHistory()}
                onStageAction={(stageKey) => setActiveStage(stageKey)}
              />
            )}

            {activeStage === "writing" && (
              <WritingStage
                stage={currentStage}
                report={reportDraft}
                outline={outlineDraft}
                selectedCount={selectedPapers.length}
                readyCount={readyCount}
                generating={reportGenerating}
                busyKey={busyKey}
                onGenerate={() => void handleGenerateReport()}
                onSave={() => void handleSaveReport()}
                onChange={updateReportDraft}
                onStageAction={(stageKey) => setActiveStage(stageKey)}
              />
            )}
          </div>
          {historyOpen && outlineHistory && (
            <OutlineHistory
              revisions={outlineHistory}
              currentId={outlineDraft?.id ?? null}
              busyKey={busyKey}
              onClose={() => setHistoryOpen(false)}
              onRestore={(revision) => void handleRestoreOutline(revision)}
            />
          )}
        </section>

        <aside className="workspace-column detail-column">
          <div className="scroll-pane">
            {activeStage === "import" && (
              <ImportDetailPane
                readyPapers={readyPapers}
                selectedNotReady={selectedNotReady}
                dismissedPapers={dismissedPapers}
                operations={operations}
                busyKey={busyKey}
                onOpenReading={(paperId) => {
                  setActiveStage("reading");
                  void handleChooseReadingPaper(paperId);
                }}
                onRemove={(paper) => void runAction(`remove-${paper.id}`, async () => {
                  if (!workspaceId) return;
                  await removePaper(workspaceId, paper.id);
                  setNotice("The paper left the current evidence boundary. Historical provenance remains intact.");
                })}
                onRetry={(paper) => void handleRetry(paper)}
                onRestore={(paper) => void handleRestorePaper(paper)}
                onUploadFileChange={(paperId, file) => setCandidateFiles((current) => ({ ...current, [paperId]: file }))}
                onCandidateUpload={(paperId, event) => void handleUpload(event, paperId)}
                candidateFiles={candidateFiles}
                onRetryOutline={(operation) => void handleRetryOutline(operation)}
                onRetryReport={(operation) => void handleRetryReport(operation)}
                onRetryIndex={(operation) => void handleRetryIndex(operation)}
              />
            )}

            {activeStage === "reading" && (
              <ReadingDetailPane
                readingState={viewState.reading_state}
                selectedNotReady={selectedNotReady}
                onChoosePaper={(paperId) => void handleChooseReadingPaper(paperId)}
                onRemovePaper={(paper) => void runAction(`remove-${paper.id}`, async () => {
                  if (!workspaceId) return;
                  await removePaper(workspaceId, paper.id);
                  setNotice("The paper left the current evidence boundary. Historical provenance remains intact.");
                })}
                onOpenImport={() => setActiveStage("import")}
              />
            )}

            {activeStage === "outline" && (
              <OutlineDetailPane
                outline={outlineDraft}
                readyCount={readyCount}
                operations={operations}
                busyKey={busyKey}
                onOpenImport={() => setActiveStage("import")}
                onRetryOutline={(operation) => void handleRetryOutline(operation)}
              />
            )}

            {activeStage === "writing" && (
              <WritingDetailPane
                report={reportDraft}
                operations={operations}
                busyKey={busyKey}
                onOpenOutline={() => setActiveStage("outline")}
                onRetryReport={(operation) => void handleRetryReport(operation)}
              />
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}

function defaultStage(key: WorkspaceStageKey): WorkspaceStageState {
  const titles: Record<WorkspaceStageKey, string> = {
    import: "Literature Import",
    reading: "Paper Reading",
    outline: "Report Outline",
    writing: "Report Writing",
  };
  return {
    key,
    title: titles[key],
    available: false,
    detail: "Stage information is loading.",
    next_action_stage: null,
    next_action_label: null,
  };
}

function StageHeader({ stage }: { stage: WorkspaceStageState }) {
  return (
    <div className="stage-header">
      <p className="eyebrow">{stage.key.toUpperCase()}</p>
      <h2>{stage.title}</h2>
      <p className="muted">{stage.detail}</p>
    </div>
  );
}

function StageUnavailable({
  stage,
  onGo,
}: {
  stage: WorkspaceStageState;
  onGo: (stage: WorkspaceStageKey) => void;
}) {
  const nextStage = stage.next_action_stage;
  return (
    <div className="callout-card">
      <strong>This stage is not ready yet.</strong>
      <p>{stage.detail}</p>
      {nextStage && stage.next_action_label && (
        <button type="button" onClick={() => onGo(nextStage)}>
          {stage.next_action_label}
        </button>
      )}
    </div>
  );
}

function ImportStage({
  workspace,
  discovery,
  discoveryQuery,
  provider,
  uploadFile,
  busyKey,
  candidateFiles,
  candidatePapers,
  onDiscoveryQueryChange,
  onProviderChange,
  onUploadFileChange,
  onDiscover,
  onUpload,
  onImport,
  onSelect,
  onDismiss,
  onCandidateFileChange,
  onCandidateUpload,
}: {
  workspace: WorkspaceViewState["workspace"];
  discovery: DiscoveryResponse | null;
  discoveryQuery: string;
  provider: "openalex" | "arxiv";
  uploadFile: File | null;
  busyKey: string | null;
  candidateFiles: Record<string, File | null>;
  candidatePapers: ResearchPaper[];
  onDiscoveryQueryChange: (value: string) => void;
  onProviderChange: (value: "openalex" | "arxiv") => void;
  onUploadFileChange: (file: File | null) => void;
  onDiscover: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onUpload: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onImport: (paper: ResearchPaper) => void;
  onSelect: (paper: ResearchPaper) => void;
  onDismiss: (paper: ResearchPaper) => void;
  onCandidateFileChange: (paperId: string, file: File | null) => void;
  onCandidateUpload: (paperId: string, event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <>
      <div className="topic-card">
        <strong>{workspace.state === "active" ? "Workspace active" : "Workspace setup"}</strong>
        <p>
          The evidence boundary is explicit: Candidate Papers remain metadata only until they become Selected Papers and
          reach evidence-ready status.
        </p>
      </div>

      <div className="card-block">
        <SectionLabel label="Upload an authorised research paper" detail="PDF only" />
        <form className="inline-form-grid" onSubmit={(event) => void onUpload(event)}>
          <label className="file-picker">
            <input
              data-testid="upload-paper"
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event: ChangeEvent<HTMLInputElement>) => onUploadFileChange(event.target.files?.[0] ?? null)}
            />
            <span>{uploadFile?.name ?? "Choose PDF file"}</span>
          </label>
          <button type="submit" disabled={!uploadFile || busyKey === "upload-paper"}>
            {busyKey === "upload-paper" ? "Submitting..." : "Upload and prepare"}
          </button>
        </form>
        <p className="helper-text">
          Uploaded papers enter the Selected Paper boundary immediately. Parsing or indexing failures stay recoverable in
          the workspace operation history.
        </p>
      </div>

      <div className="card-block">
        <SectionLabel label="Discover open papers" detail="OpenAlex or arXiv" />
        <form className="discovery-form" onSubmit={(event) => void onDiscover(event)}>
          <input
            data-testid="discovery-query"
            value={discoveryQuery}
            onChange={(event) => onDiscoveryQueryChange(event.target.value)}
            placeholder="Search by topic"
          />
          <select value={provider} onChange={(event) => onProviderChange(event.target.value as "openalex" | "arxiv")} aria-label="Discovery provider">
            <option value="openalex">OpenAlex</option>
            <option value="arxiv">arXiv</option>
          </select>
          <button data-testid="discovery-submit" type="submit" disabled={!discoveryQuery.trim() || busyKey === "discover"}>
            {busyKey === "discover" ? "Searching..." : "Search candidates"}
          </button>
        </form>
        {discovery && <DiscoverySummary discovery={discovery} onSwitchToArxiv={() => onProviderChange("arxiv")} />}
      </div>

      <div className="card-block">
        <SectionLabel label="Candidate Papers" detail="Not evidence until selected" />
        {candidatePapers.length ? (
          candidatePapers.map((paper) => (
            <PaperCard
              key={paper.id}
              paper={paper}
              candidate
              busyKey={busyKey}
              onImport={() => onImport(paper)}
              onSelect={() => onSelect(paper)}
              onDismiss={() => onDismiss(paper)}
              onUpload={(file) => onCandidateFileChange(paper.id, file)}
              candidateFile={candidateFiles[paper.id] ?? null}
              onCandidateUpload={(event) => onCandidateUpload(paper.id, event)}
            />
          ))
        ) : (
          <EmptyState text="Run discovery to populate the Candidate Paper list." />
        )}
      </div>
    </>
  );
}

function ImportDetailPane({
  readyPapers,
  selectedNotReady,
  dismissedPapers,
  operations,
  busyKey,
  onOpenReading,
  onRemove,
  onRetry,
  onRestore,
  onUploadFileChange,
  onCandidateUpload,
  candidateFiles,
  onRetryOutline,
  onRetryReport,
  onRetryIndex,
}: {
  readyPapers: ResearchPaper[];
  selectedNotReady: ResearchPaper[];
  dismissedPapers: ResearchPaper[];
  operations: WorkspaceOperation[];
  busyKey: string | null;
  onOpenReading: (paperId: string) => void;
  onRemove: (paper: ResearchPaper) => void;
  onRetry: (paper: ResearchPaper) => void;
  onRestore: (paper: ResearchPaper) => void;
  onUploadFileChange: (paperId: string, file: File | null) => void;
  onCandidateUpload: (paperId: string, event: FormEvent<HTMLFormElement>) => void;
  candidateFiles: Record<string, File | null>;
  onRetryOutline: (operation: WorkspaceOperation) => void;
  onRetryReport: (operation: WorkspaceOperation) => void;
  onRetryIndex: (operation: WorkspaceOperation) => void;
}) {
  return (
    <>
      <DetailSection title="Ready paper collection" subtitle="Only ready papers can be read, retrieved, or cited.">
        {readyPapers.length ? (
          readyPapers.map((paper) => (
            <div className="library-row-group" key={paper.id}>
              <button
                type="button"
                className="library-row"
                data-testid={`ready-paper-row-${paper.id}`}
                onClick={() => onOpenReading(paper.id)}
              >
                <span>
                  <strong>{paper.title}</strong>
                  <small>{paper.authors.slice(0, 2).join(", ") || "Authors unavailable"}</small>
                </span>
                <span className="mini-badge mini-badge-success">Read</span>
              </button>
              <button
                type="button"
                className="button-quiet library-row-action"
                data-testid={`remove-paper-${paper.id}`}
                onClick={() => onRemove(paper)}
              >
                Remove
              </button>
            </div>
          ))
        ) : (
          <EmptyState text="No Selected Paper is evidence-ready yet." />
        )}
      </DetailSection>

      <DetailSection title="Selected papers in preparation" subtitle="Recover failures and track readiness truthfully.">
        {selectedNotReady.length ? (
          selectedNotReady.map((paper) => (
            <PaperCard
              key={paper.id}
              paper={paper}
              selected
              busyKey={busyKey}
              onRemove={() => onRemove(paper)}
              onRetry={() => onRetry(paper)}
              onUpload={(file) => onUploadFileChange(paper.id, file)}
              candidateFile={candidateFiles[paper.id] ?? null}
              onCandidateUpload={(event) => onCandidateUpload(paper.id, event)}
            />
          ))
        ) : (
          <EmptyState text="Every Selected Paper is either ready or the set is still empty." />
        )}
      </DetailSection>

      <DetailSection title="Dismissed candidates" subtitle="Restore papers you want to reconsider for this workspace.">
        {dismissedPapers.length ? (
          dismissedPapers.map((paper) => (
            <PaperCard
              key={paper.id}
              paper={paper}
              dismissed
              busyKey={busyKey}
              onRestore={() => onRestore(paper)}
            />
          ))
        ) : (
          <EmptyState text="Dismissed Candidate Papers will appear here until you restore them." />
        )}
      </DetailSection>

      <DetailSection title="Workspace operations" subtitle="Durable progress, failure, and retry history.">
        {operations.length ? (
          operations.map((operation) => (
            <OperationCard
              key={operation.id}
              operation={operation}
              papers={[...readyPapers, ...selectedNotReady]}
              busyKey={busyKey}
              onRetry={onRetry}
              onRetryOutline={onRetryOutline}
              onRetryReport={onRetryReport}
              onRetryIndex={onRetryIndex}
            />
          ))
        ) : (
          <EmptyState text="Operation history will appear here after uploads, imports, or generation steps." />
        )}
      </DetailSection>
    </>
  );
}

function ReadingStage({
  stage,
  readingState,
  onStageAction,
}: {
  stage: WorkspaceStageState;
  readingState: WorkspaceViewState["reading_state"];
  onStageAction: (stage: WorkspaceStageKey) => void;
}) {
  const paper = readingState.active_paper;
  return (
    <>
      {!stage.available && <StageUnavailable stage={stage} onGo={onStageAction} />}
      {paper ? (
        <div className="reading-stage">
          <div className="reading-meta">
            <strong>{paper.title}</strong>
            <p>{paper.authors.join(", ") || "Author metadata unavailable"}</p>
            <span className={`badge badge-${paper.evidence_readiness}`}>{readinessLabels[paper.evidence_readiness]}</span>
          </div>
          {readingState.pdf_available && readingState.pdf_url ? (
            <iframe
              data-testid="paper-reading-frame"
              title={`Original PDF: ${paper.title}`}
              src={readingState.pdf_url}
              className="pdf-frame"
            />
          ) : (
            <div className="reading-unavailable">
              <strong>Original PDF unavailable</strong>
              <p>{readingState.unavailable_reason || "The workspace cannot show a reconstructed reader for this paper."}</p>
              {paper.source_url && (
                <a href={paper.source_url} target="_blank" rel="noreferrer">
                  Open source page
                </a>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="callout-card">
          <strong>No paper is selected for reading.</strong>
          <p>Prepare at least one Selected Paper until it becomes evidence-ready, then open it here.</p>
          <button type="button" onClick={() => onStageAction("import")}>
            Go to Literature Import
          </button>
        </div>
      )}
    </>
  );
}

function ReadingDetailPane({
  readingState,
  selectedNotReady,
  onChoosePaper,
  onRemovePaper,
  onOpenImport,
}: {
  readingState: WorkspaceViewState["reading_state"];
  selectedNotReady: ResearchPaper[];
  onChoosePaper: (paperId: string) => void;
  onRemovePaper: (paper: ResearchPaper) => void;
  onOpenImport: () => void;
}) {
  return (
    <>
      <DetailSection title="Ready paper library" subtitle="Switch the active original PDF.">
        {readingState.ready_papers.length ? (
          readingState.ready_papers.map((paper) => (
            <div className="library-row-group" key={paper.id}>
              <button
                type="button"
                className={readingState.active_paper_id === paper.id ? "library-row library-row-active" : "library-row"}
                data-testid={`reading-paper-${paper.id}`}
                onClick={() => onChoosePaper(paper.id)}
              >
                <span>
                  <strong>{paper.title}</strong>
                  <small>{paper.year || "Year unavailable"}</small>
                </span>
                <span className="mini-badge">Ready</span>
              </button>
              <button
                type="button"
                className="button-quiet library-row-action"
                data-testid={`reading-remove-paper-${paper.id}`}
                onClick={() => onRemovePaper(paper)}
              >
                Remove
              </button>
            </div>
          ))
        ) : (
          <EmptyState text="The reading library fills only with evidence-ready Selected Papers." />
        )}
      </DetailSection>

      <DetailSection title="Still preparing" subtitle="Unavailable stages explain the next permitted action.">
        {selectedNotReady.length ? (
          selectedNotReady.map((paper) => (
            <div className="detail-note" key={paper.id}>
              <strong>{paper.title}</strong>
              <p>{paperFailureMessage(paper) || `Status: ${readinessLabels[paper.evidence_readiness]}`}</p>
            </div>
          ))
        ) : (
          <EmptyState text="No additional Selected Papers are waiting on preparation." />
        )}
        <button type="button" className="button-quiet" onClick={onOpenImport}>
          Open Literature Import
        </button>
      </DetailSection>
    </>
  );
}

function OutlineStage({
  stage,
  outline,
  readyCount,
  generating,
  busyKey,
  onGenerate,
  onSave,
  onApprove,
  onChange,
  onAddSection,
  onMoveSection,
  onOpenHistory,
  onStageAction,
}: {
  stage: WorkspaceStageState;
  outline: ReportOutline | null;
  readyCount: number;
  generating: boolean;
  busyKey: string | null;
  onGenerate: () => void;
  onSave: () => void;
  onApprove: () => void;
  onChange: (update: (outline: ReportOutline) => ReportOutline) => void;
  onAddSection: () => void;
  onMoveSection: (index: number, offset: -1 | 1) => void;
  onOpenHistory: () => void;
  onStageAction: (stage: WorkspaceStageKey) => void;
}) {
  if (!stage.available) return <StageUnavailable stage={stage} onGo={onStageAction} />;
  return (
    <OutlineEditor
      outline={outline}
      readyCount={readyCount}
      generating={generating}
      busyKey={busyKey}
      onGenerate={onGenerate}
      onSave={onSave}
      onApprove={onApprove}
      onChange={onChange}
      onAddSection={onAddSection}
      onMoveSection={onMoveSection}
      onOpenHistory={onOpenHistory}
    />
  );
}

function WritingStage({
  stage,
  report,
  outline,
  selectedCount,
  readyCount,
  generating,
  busyKey,
  onGenerate,
  onSave,
  onChange,
  onStageAction,
}: {
  stage: WorkspaceStageState;
  report: LiteratureReport | null;
  outline: ReportOutline | null;
  selectedCount: number;
  readyCount: number;
  generating: boolean;
  busyKey: string | null;
  onGenerate: () => void;
  onSave: () => void;
  onChange: (update: (report: LiteratureReport) => LiteratureReport) => void;
  onStageAction: (stage: WorkspaceStageKey) => void;
}) {
  if (!stage.available) return <StageUnavailable stage={stage} onGo={onStageAction} />;
  return (
    <ReportEditor
      report={report}
      outline={outline}
      selectedCount={selectedCount}
      readyCount={readyCount}
      generating={generating}
      busyKey={busyKey}
      onGenerate={onGenerate}
      onSave={onSave}
      onChange={onChange}
    />
  );
}

function OutlineDetailPane({
  outline,
  readyCount,
  operations,
  busyKey,
  onOpenImport,
  onRetryOutline,
}: {
  outline: ReportOutline | null;
  readyCount: number;
  operations: WorkspaceOperation[];
  busyKey: string | null;
  onOpenImport: () => void;
  onRetryOutline: (operation: WorkspaceOperation) => void;
}) {
  const outlineOps = operations.filter((operation) => operation.operation_type === "generate_outline");
  return (
    <>
      <DetailSection title="Outline status" subtitle="Query-controlled retrieval starts from this stage.">
        {outline ? (
          <div className="detail-note">
            <strong>{outline.title}</strong>
            <p>Revision {outline.revision_number} | {outline.status === "approved" ? "Approved" : "Draft"}</p>
            <p>{outline.research_question}</p>
          </div>
        ) : (
          <EmptyState text="Generate an outline after at least one Selected Paper becomes evidence-ready." />
        )}
        <div className="detail-note">
          <strong>{readyCount}</strong>
          <p>evidence-ready papers currently available to outline generation</p>
        </div>
        <button type="button" className="button-quiet" onClick={onOpenImport}>
          Open Literature Import
        </button>
      </DetailSection>

      <DetailSection title="Outline operations" subtitle="Retry preserved operation history when needed.">
        {outlineOps.length ? (
          outlineOps.map((operation) => (
            <OperationCard
              key={operation.id}
              operation={operation}
              papers={[]}
              busyKey={busyKey}
              onRetry={() => undefined}
              onRetryOutline={onRetryOutline}
              onRetryReport={() => undefined}
              onRetryIndex={() => undefined}
            />
          ))
        ) : (
          <EmptyState text="Outline generation history appears here when that stage runs." />
        )}
      </DetailSection>
    </>
  );
}

function WritingDetailPane({
  report,
  operations,
  busyKey,
  onOpenOutline,
  onRetryReport,
}: {
  report: LiteratureReport | null;
  operations: WorkspaceOperation[];
  busyKey: string | null;
  onOpenOutline: () => void;
  onRetryReport: (operation: WorkspaceOperation) => void;
}) {
  const reportOps = operations.filter((operation) => operation.operation_type === "generate_report");
  return (
    <>
      <DetailSection title="Report trust summary" subtitle="Keep evidence coverage explicit.">
        {report ? (
          <div className="detail-note">
            <strong>{report.title}</strong>
            <p>
              Included papers: {report.evidence_coverage.included_paper_ids.length} | Excluded papers:{" "}
              {report.evidence_coverage.excluded_papers.length}
            </p>
            <p>
              Claims: {report.sections.reduce((total, section) => total + section.claims.length, 0)} | Status:{" "}
              {report.status}
            </p>
          </div>
        ) : (
          <EmptyState text="Generate a report after approving the current outline." />
        )}
        <button type="button" className="button-quiet" onClick={onOpenOutline}>
          Open Report Outline
        </button>
      </DetailSection>

      <DetailSection title="Report operations" subtitle="Report retries never overwrite the current draft immediately.">
        {reportOps.length ? (
          reportOps.map((operation) => (
            <OperationCard
              key={operation.id}
              operation={operation}
              papers={[]}
              busyKey={busyKey}
              onRetry={() => undefined}
              onRetryOutline={() => undefined}
              onRetryReport={onRetryReport}
              onRetryIndex={() => undefined}
            />
          ))
        ) : (
          <EmptyState text="Report generation history appears here when the writing stage runs." />
        )}
      </DetailSection>
    </>
  );
}

function OutlineEditor({
  outline,
  readyCount,
  generating,
  busyKey,
  onGenerate,
  onSave,
  onApprove,
  onChange,
  onAddSection,
  onMoveSection,
  onOpenHistory,
}: {
  outline: ReportOutline | null;
  readyCount: number;
  generating: boolean;
  busyKey: string | null;
  onGenerate: () => void;
  onSave: () => void;
  onApprove: () => void;
  onChange: (update: (outline: ReportOutline) => ReportOutline) => void;
  onAddSection: () => void;
  onMoveSection: (index: number, offset: -1 | 1) => void;
  onOpenHistory: () => void;
}) {
  if (!outline) {
    return (
      <div className="card-block" data-testid="outline-editor">
        <SectionLabel label="Report Outline" detail="Approve structure before report generation" />
        <p className="helper-text">
          {readyCount > 0
            ? "Evidence-ready Selected Papers are available, so the workspace can generate an initial outline now."
            : "Prepare at least one Selected Paper until it becomes evidence-ready before generating the outline."}
        </p>
        <button data-testid="outline-generate" type="button" onClick={onGenerate} disabled={readyCount === 0 || generating || busyKey === "generate-outline"}>
          {busyKey === "generate-outline" ? "Generating..." : "Generate outline"}
        </button>
      </div>
    );
  }

  return (
    <div className="card-block" data-testid="outline-editor">
      <div className="outline-heading">
        <SectionLabel label="Report Outline" detail={`Revision ${outline.revision_number}`} />
        <div className="outline-heading-actions">
          <span className={`mini-badge ${outline.status === "approved" ? "mini-badge-success" : ""}`} data-testid="outline-status">
            {outline.status === "approved" ? "Approved" : "Draft"}
          </span>
          <button type="button" className="button-quiet" data-testid="outline-history" onClick={onOpenHistory}>
            History
          </button>
        </div>
      </div>

      <label className="field-block">
        Title
        <input data-testid="outline-title" value={outline.title} onChange={(event) => onChange((current) => ({ ...current, title: event.target.value }))} />
      </label>
      <label className="field-block">
        Research question
        <textarea
          data-testid="outline-research-question"
          rows={3}
          value={outline.research_question}
          onChange={(event) => onChange((current) => ({ ...current, research_question: event.target.value }))}
        />
      </label>

      <div className="outline-section-list">
        {outline.sections.map((section, index) => (
          <article className="outline-section" data-testid="outline-section" key={section.id}>
            <div className="outline-section-toolbar">
              <span>{index + 1}</span>
              <button type="button" aria-label="Move section up" onClick={() => onMoveSection(index, -1)} disabled={index === 0}>
                Up
              </button>
              <button type="button" aria-label="Move section down" onClick={() => onMoveSection(index, 1)} disabled={index === outline.sections.length - 1}>
                Down
              </button>
              <button
                type="button"
                className="button-quiet"
                onClick={() => onChange((current) => ({ ...current, sections: current.sections.filter((item) => item.id !== section.id) }))}
                disabled={outline.sections.length <= 1}
              >
                Delete
              </button>
            </div>
            <input
              data-testid={`outline-section-title-${section.id}`}
              value={section.title}
              aria-label={`Section ${index + 1} title`}
              onChange={(event) =>
                onChange((current) => ({
                  ...current,
                  sections: current.sections.map((item) => (item.id === section.id ? { ...item, title: event.target.value } : item)),
                }))
              }
            />
            <textarea
              value={section.description}
              rows={2}
              aria-label={`Section ${index + 1} description`}
              onChange={(event) =>
                onChange((current) => ({
                  ...current,
                  sections: current.sections.map((item) => (item.id === section.id ? { ...item, description: event.target.value } : item)),
                }))
              }
            />
          </article>
        ))}
      </div>

      <div className="outline-actions">
        <button type="button" className="button-quiet" data-testid="outline-add-section" onClick={onAddSection}>
          Add section
        </button>
        <button type="button" data-testid="outline-save" onClick={onSave} disabled={busyKey === "save-outline"}>
          {busyKey === "save-outline" ? "Saving..." : "Save draft"}
        </button>
        {outline.status === "draft" && (
          <button type="button" data-testid="outline-approve" onClick={onApprove} disabled={busyKey === "approve-outline"}>
            {busyKey === "approve-outline" ? "Approving..." : "Approve this revision"}
          </button>
        )}
      </div>
      <p className="helper-text">
        {outline.status === "approved"
          ? "Editing an approved revision creates a new draft revision rather than mutating history."
          : "Edit, reorder, add, or remove sections before approving the current revision."}
      </p>
    </div>
  );
}

function ReportEditor({
  report,
  outline,
  selectedCount,
  readyCount,
  generating,
  busyKey,
  onGenerate,
  onSave,
  onChange,
}: {
  report: LiteratureReport | null;
  outline: ReportOutline | null;
  selectedCount: number;
  readyCount: number;
  generating: boolean;
  busyKey: string | null;
  onGenerate: () => void;
  onSave: () => void;
  onChange: (update: (report: LiteratureReport) => LiteratureReport) => void;
}) {
  const approved = outline?.status === "approved";
  if (!approved) {
    return (
      <div className="card-block" data-testid="report-editor">
        <SectionLabel label="Literature Report" detail="Approve the outline before writing" />
        <p className="helper-text">
          The writing stage publishes a continuous draft only after the current outline is approved and report generation succeeds.
        </p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="card-block" data-testid="report-editor">
        <SectionLabel label="Literature Report" detail="Continuous cited draft" />
        <p className="helper-text">
          Report generation uses only evidence-ready Selected Papers. Current readiness: {readyCount}/{selectedCount}.
        </p>
        <button data-testid="report-generate" type="button" onClick={onGenerate} disabled={readyCount === 0 || generating || busyKey === "generate-report"}>
          {generating || busyKey === "generate-report"
            ? "Generating..."
            : readyCount < selectedCount
              ? "Generate from ready subset"
              : "Generate cited report"}
        </button>
      </div>
    );
  }

  return (
    <div className="card-block" data-testid="report-editor">
      <div className="outline-heading">
        <SectionLabel label="Literature Report" detail={report.language === "zh" ? "Chinese draft" : "English draft"} />
        <span className={`mini-badge ${report.status === "ready" ? "mini-badge-success" : ""}`} data-testid="report-status">
          {report.status === "ready" ? "Evidence linked" : "Needs attention"}
        </span>
      </div>

      <label className="field-block">
        Report title
        <input data-testid="report-title" value={report.title} onChange={(event) => onChange((current) => ({ ...current, title: event.target.value }))} />
      </label>
      <label className="field-block">
        Overview
        <textarea data-testid="report-overview" rows={3} value={report.overview} onChange={(event) => onChange((current) => ({ ...current, overview: event.target.value }))} />
      </label>

      <div className="report-trust-summary" data-testid="report-trust-summary">
        <strong>Evidence coverage</strong>
        <span>Included: {report.evidence_coverage.included_paper_ids.length}</span>
        <span>Excluded: {report.evidence_coverage.excluded_papers.length}</span>
        <span>Claims: {report.sections.reduce((total, section) => total + section.claims.length, 0)}</span>
      </div>

      {report.evidence_coverage.excluded_papers.length > 0 && (
        <p className="helper-text">This draft explicitly excludes not-ready Selected Papers from its evidence coverage.</p>
      )}
      {report.gap_notes.length > 0 && (
        <div className="report-gap-notes" data-testid="report-evidence-gap">
          <strong>Evidence gaps</strong>
          {report.gap_notes.map((note, index) => (
            <p key={`${note}-${index}`}>{note}</p>
          ))}
        </div>
      )}

      <div className="report-section-list">
        {report.sections.map((section) => (
          <article className="report-section" data-testid="report-section" key={section.id}>
            <h3>{section.title}</h3>
            {section.claims.map((claim) => (
              <div className={`report-claim ${claim.claim_type === "evidence_gap" ? "report-claim-gap" : ""}`} data-testid="report-claim" key={claim.id}>
                <textarea
                  data-testid={`report-claim-${claim.id}`}
                  aria-label={`${section.title} Claim`}
                  rows={4}
                  value={claim.text}
                  onChange={(event) =>
                    onChange((current) => ({
                      ...current,
                      sections: current.sections.map((item) =>
                        item.id === section.id
                          ? {
                              ...item,
                              claims: item.claims.map((candidate) => (candidate.id === claim.id ? { ...candidate, text: event.target.value } : candidate)),
                            }
                          : item,
                      ),
                    }))
                  }
                />
                {claim.citations.length > 0 ? (
                  <span className="citation-marker" data-testid={`claim-citations-${claim.id}`}>
                    Verified citations: {claim.citations.reduce((total, citation) => total + citation.source_chunk_ids.length, 0)} source chunks
                  </span>
                ) : (
                  <span className="citation-marker citation-gap">No valid citations attached</span>
                )}
              </div>
            ))}
          </article>
        ))}
      </div>

      <div className="outline-actions">
        <button type="button" data-testid="report-save" onClick={onSave} disabled={busyKey === "save-report"}>
          {busyKey === "save-report" ? "Saving..." : "Save report draft"}
        </button>
      </div>
      <p className="helper-text">
        Browser edits auto-save. Failed generation or missing evidence keeps explicit gap and operation state instead of publishing a synthetic draft.
      </p>
    </div>
  );
}

function OutlineHistory({
  revisions,
  currentId,
  busyKey,
  onClose,
  onRestore,
}: {
  revisions: ReportOutline[];
  currentId: string | null;
  busyKey: string | null;
  onClose: () => void;
  onRestore: (revision: ReportOutline) => void;
}) {
  return (
    <div className="outline-history-backdrop" data-testid="outline-history-panel" role="dialog" aria-modal="true" aria-label="Outline history">
      <aside className="outline-history-drawer">
        <div className="outline-heading">
          <SectionLabel label="Outline History" detail={`${revisions.length} revisions`} />
          <button type="button" className="button-quiet" onClick={onClose}>
            Close
          </button>
        </div>
        {revisions.length ? (
          <div className="history-list">
            {revisions.map((revision) => (
              <article className="history-item" data-testid="outline-history-item" key={revision.id}>
                <div className="history-item-heading">
                  <strong>Revision {revision.revision_number}</strong>
                  <span className={`mini-badge ${revision.status === "approved" ? "mini-badge-success" : ""}`}>
                    {revision.status === "approved" ? "Approved" : "Draft"}
                  </span>
                </div>
                <p>{revision.title}</p>
                <p className="history-summary">
                  <strong>Research question:</strong> {revision.research_question}
                </p>
                <ul className="history-sections">
                  {revision.sections.map((section) => (
                    <li key={section.id}>
                      <strong>{section.title}</strong>
                      {section.description && `: ${section.description}`}
                    </li>
                  ))}
                </ul>
                <small>{revision.updated_at ? new Date(revision.updated_at).toLocaleString("en-US") : "Time unknown"}</small>
                <div className="history-item-actions">
                  {revision.id === currentId ? (
                    <span className="muted">Current revision</span>
                  ) : (
                    <button type="button" onClick={() => onRestore(revision)} disabled={busyKey === `restore-outline-${revision.id}`}>
                      {busyKey === `restore-outline-${revision.id}` ? "Restoring..." : "Restore as new draft"}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState text="No outline history is available yet." />
        )}
      </aside>
    </div>
  );
}

function WorkspaceForm({
  compact = false,
  topic,
  language,
  submitLabel,
  onTopicChange,
  onLanguageChange,
  onSubmit,
  busy,
}: {
  compact?: boolean;
  topic: string;
  language: ReportLanguage;
  submitLabel: string;
  onTopicChange: (value: string) => void;
  onLanguageChange: (value: ReportLanguage) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  busy: boolean;
}) {
  if (compact) {
    return (
      <form className="compact-create-form" onSubmit={onSubmit}>
        <input data-testid="workspace-topic" value={topic} onChange={(event) => onTopicChange(event.target.value)} placeholder="New research topic" />
        <div className="inline-form">
          <select value={language} onChange={(event) => onLanguageChange(event.target.value as ReportLanguage)} aria-label="Report language">
            <option value="zh">Chinese report</option>
            <option value="en">English report</option>
          </select>
          <button data-testid="workspace-create" type="submit" disabled={!topic.trim() || busy}>
            {busy ? "Creating..." : submitLabel}
          </button>
        </div>
      </form>
    );
  }

  return (
    <form className="create-form" onSubmit={onSubmit}>
      <label>
        Research topic
        <input
          data-testid="workspace-topic"
          value={topic}
          onChange={(event) => onTopicChange(event.target.value)}
          placeholder="For example: traceable research evidence"
          autoFocus
        />
      </label>
      <label>
        Report language
        <select value={language} onChange={(event) => onLanguageChange(event.target.value as ReportLanguage)}>
          <option value="zh">Chinese</option>
          <option value="en">English</option>
        </select>
      </label>
      <button data-testid="workspace-create" type="submit" disabled={!topic.trim() || busy}>
        {busy ? "Creating..." : submitLabel}
      </button>
    </form>
  );
}

function PaperCard({
  paper,
  selected = false,
  candidate = false,
  dismissed = false,
  onImport,
  onSelect,
  onRemove,
  onDismiss,
  onRestore,
  onRetry,
  onUpload,
  candidateFile,
  onCandidateUpload,
  busyKey,
}: {
  paper: ResearchPaper;
  selected?: boolean;
  candidate?: boolean;
  dismissed?: boolean;
  onImport?: () => void;
  onSelect?: () => void;
  onRemove?: () => void;
  onDismiss?: () => void;
  onRestore?: () => void;
  onRetry?: () => void;
  onUpload?: (file: File) => void;
  candidateFile?: File | null;
  onCandidateUpload?: (event: FormEvent<HTMLFormElement>) => void;
  busyKey: string | null;
}) {
  const importKey = `import-${paper.id}`;
  const selectKey = `select-${paper.id}`;
  const removeKey = `remove-${paper.id}`;
  const dismissKey = `dismiss-${paper.id}`;
  const restoreKey = `restore-${paper.id}`;
  const retryKey = `retry-${paper.id}`;
  const uploadKey = `upload-${paper.id}`;
  const needsAuthorisedFile = paper.evidence_readiness === "awaiting_authorised_file" || paper.evidence_readiness === "failed";
  const hasPdf = Boolean(paper.pdf_urls?.length || paper.pdf_url);

  return (
    <article
      className={`paper-card ${paper.evidence_eligible ? "paper-card-ready" : ""}`}
      data-testid={dismissed ? "paper-dismissed" : candidate ? "paper-candidate" : selected ? "paper-selected" : "paper-unselected"}
    >
      <div className="paper-card-heading">
        <div>
          <h3>{paper.title}</h3>
          <p>{paper.authors.slice(0, 3).join(" | ") || "Author metadata unavailable"}{paper.year && ` | ${paper.year}`}</p>
        </div>
        <span className={`badge badge-${paper.evidence_readiness}`}>{paper.evidence_eligible ? "Evidence ready" : readinessLabels[paper.evidence_readiness]}</span>
      </div>
      {paper.venue && <p className="paper-venue">{paper.venue}</p>}
      {paper.abstract && <p className="paper-abstract">{paper.abstract}</p>}
      {paper.source_url && (
        <a className="paper-link" href={paper.source_url} target="_blank" rel="noreferrer">
          Open source page
        </a>
      )}
      {!dismissed && paperFailureMessage(paper) && <p className="paper-failure">{paperFailureMessage(paper)}</p>}
      <div className="paper-actions">
        {candidate && onImport && (
          <button data-testid={`import-paper-${paper.id}`} type="button" onClick={onImport} disabled={busyKey === importKey}>
            {busyKey === importKey ? "Submitting..." : hasPdf && paper.is_open_access !== false ? "Try open PDF import" : "Prepare authorised PDF"}
          </button>
        )}
        {candidate && onSelect && (
          <button className="button-quiet" data-testid={`select-paper-${paper.id}`} type="button" onClick={onSelect} disabled={busyKey === selectKey}>
            Select first
          </button>
        )}
        {candidate && onDismiss && (
          <button className="button-quiet" data-testid={`dismiss-paper-${paper.id}`} type="button" onClick={onDismiss} disabled={busyKey === dismissKey}>
            Dismiss
          </button>
        )}
        {!candidate && !dismissed && onSelect && (
          <button type="button" onClick={onSelect} disabled={busyKey === selectKey}>
            {busyKey === selectKey ? "Updating..." : "Add to Selected Papers"}
          </button>
        )}
        {selected && onRemove && (
          <button className="button-quiet" data-testid={`remove-paper-${paper.id}`} type="button" onClick={onRemove} disabled={busyKey === removeKey}>
            Remove from boundary
          </button>
        )}
        {dismissed && onRestore && (
          <button type="button" data-testid={`restore-paper-${paper.id}`} onClick={onRestore} disabled={busyKey === restoreKey}>
            {busyKey === restoreKey ? "Restoring..." : "Restore candidate"}
          </button>
        )}
        {paper.retryable && onRetry && (
          <button className="button-warning" data-testid={`retry-paper-${paper.id}`} type="button" onClick={onRetry} disabled={busyKey === retryKey}>
            {busyKey === retryKey ? "Retrying..." : "Retry preparation"}
          </button>
        )}
      </div>
      {needsAuthorisedFile && onCandidateUpload && (
        <form className="authorised-upload" onSubmit={onCandidateUpload}>
          <label className="file-picker compact">
            <input
              data-testid={`authorised-upload-${paper.id}`}
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                const file = event.target.files?.[0];
                if (file) onUpload?.(file);
              }}
            />
            <span>{candidateFile?.name ?? "Choose authorised PDF"}</span>
          </label>
          <button type="submit" disabled={!candidateFile || busyKey === uploadKey}>
            {busyKey === uploadKey ? "Submitting..." : "Upload authorised PDF"}
          </button>
        </form>
      )}
    </article>
  );
}

function OperationCard({
  operation,
  papers,
  onRetry,
  onRetryOutline,
  onRetryReport,
  onRetryIndex,
  busyKey,
}: {
  operation: WorkspaceOperation;
  papers: ResearchPaper[];
  onRetry: (paper: ResearchPaper) => void;
  onRetryOutline: (operation: WorkspaceOperation) => void;
  onRetryReport: (operation: WorkspaceOperation) => void;
  onRetryIndex: (operation: WorkspaceOperation) => void;
  busyKey: string | null;
}) {
  const paper = papers.find((item) => item.id === operation.paper_id);
  const percent = operation.total_work ? Math.round((operation.completed_work / operation.total_work) * 100) : 0;
  const active = operation.status === "queued" || operation.status === "running";
  const retryKey = `retry-${operation.id}`;
  const canRetry = Boolean(operation.retry_action || operation.status === "failed" || operation.status === "interrupted");

  return (
    <article className="operation-card" data-testid="operation-status">
      <div className="operation-heading">
        <strong>{operationLabels[operation.operation_type] || "Workspace operation"}</strong>
        <span className={`mini-badge status-${operation.status}`}>{operationStatusLabels[operation.status]}</span>
      </div>
      <p className="operation-paper">{paper?.title || "Workspace-level operation"}</p>
      <div className="progress-track">
        <span style={{ width: `${active ? Math.max(percent, operation.phase === "importing" ? 10 : 35) : percent}%` }} />
      </div>
      <div className="operation-meta">
        <span>{phaseLabels[operation.phase] || operation.phase}</span>
        <span>
          {operation.completed_work}/{operation.total_work}
        </span>
      </div>
      {operationErrorMessage(operation) && <p className="operation-error">{operationErrorMessage(operation)}</p>}
      {canRetry && operation.operation_type === "generate_outline" && (
        <button className="button-warning full-width" type="button" onClick={() => onRetryOutline(operation)} disabled={busyKey === retryKey}>
          Retry outline generation
        </button>
      )}
      {canRetry && operation.operation_type === "generate_report" && (
        <button className="button-warning full-width" type="button" onClick={() => onRetryReport(operation)} disabled={busyKey === retryKey}>
          Retry report generation
        </button>
      )}
      {canRetry && operation.operation_type === "rebuild_evidence_index" && (
        <button className="button-warning full-width" type="button" onClick={() => onRetryIndex(operation)} disabled={busyKey === retryKey}>
          Retry evidence index
        </button>
      )}
      {canRetry && paper && operation.operation_type !== "rebuild_evidence_index" && operation.operation_type !== "generate_outline" && operation.operation_type !== "generate_report" && (
        <button className="button-warning full-width" type="button" onClick={() => onRetry(paper)} disabled={busyKey === `retry-${paper.id}`}>
          Recover this paper
        </button>
      )}
    </article>
  );
}

function DiscoverySummary({ discovery, onSwitchToArxiv }: { discovery: DiscoveryResponse; onSwitchToArxiv: () => void }) {
  const failed = discovery.status === "retryable_error" || discovery.status === "failed";
  const canSwitchToArxiv = discovery.provider === "openalex";
  const message = failed && canSwitchToArxiv && discovery.next_action === "configure_openalex_api_key"
    ? "OpenAlex requires OPENALEX_API_KEY in this environment. You can switch to arXiv immediately."
    : failed && discovery.retry_after_seconds
      ? `The provider is rate limited. Retry in about ${discovery.retry_after_seconds} seconds.`
      : failed
        ? "Paper discovery failed for now. Retry or switch providers."
        : "Candidate metadata was stored in the workspace. Review each result before it becomes evidence.";

  return (
    <div className={`discovery-result discovery-${discovery.status}`} data-testid="discovery-results">
      <strong>
        {discovery.status === "succeeded"
          ? `Stored ${discovery.candidates.length} candidates`
          : discovery.status === "empty"
            ? "No candidates found"
            : "Discovery failed"}
      </strong>
      <span>{message}</span>
      {failed && canSwitchToArxiv && (
        <button type="button" className="button-quiet" onClick={onSwitchToArxiv}>
          Switch to arXiv
        </button>
      )}
    </div>
  );
}

function SectionLabel({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="section-label">
      <strong>{label}</strong>
      <span>{detail}</span>
    </div>
  );
}

function DetailSection({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="detail-section">
      <SectionLabel label={title} detail={subtitle} />
      {children}
    </section>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="empty-state">{text}</p>;
}

function StatusBanner({ tone, text }: { tone: "success" | "danger"; text: string }) {
  return <div className={tone === "success" ? "status-banner status-banner-success" : "status-banner status-banner-danger"}>{text}</div>;
}

createRoot(document.getElementById("root")!).render(<App />);
