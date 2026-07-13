import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import {
  approveOutline,
  createWorkspace,
  discoverPapers,
  dismissPaper,
  generateOutline,
  getWorkspace,
  importPaper,
  listOutlineRevisions,
  listWorkspaces,
  removePaper,
  restoreOutlineRevision,
  restorePaper,
  retryOperation,
  retryPaper,
  saveOutline,
  selectPaper,
  uploadPaper,
  ApiRequestError,
} from "./api";
import type {
  DiscoveryResponse,
  EvidenceReadiness,
  ResearchPaper,
  ResearchWorkspace,
  ReportLanguage,
  ReportOutline,
  WorkspaceOperation,
} from "./types";
import "./styles.css";

const readinessLabels: Record<EvidenceReadiness, string> = {
  awaiting_authorised_file: "等待授权文件",
  importing: "正在导入",
  parsing: "正在解析",
  indexing: "正在建立索引",
  ready: "证据就绪",
  failed: "处理失败",
  unavailable: "尚未导入",
};

const operationLabels: Record<string, string> = {
  import_paper: "上传论文",
  import_authorised_paper: "上传授权文件",
  import_discovered_paper: "导入开放论文",
  retry_paper_import: "重试论文处理",
  generate_outline: "生成报告大纲",
};

const operationStatusLabels: Record<WorkspaceOperation["status"], string> = {
  queued: "排队中",
  running: "处理中",
  succeeded: "已完成",
  failed: "失败",
  interrupted: "已中断",
  cancelled: "已取消",
};

const phaseLabels: Record<string, string> = {
  importing: "导入",
  parsing: "解析",
  indexing: "索引",
  ready: "就绪",
  generating: "生成",
  draft_ready: "草稿已生成",
  interrupted: "中断",
};

function localizeError(reason: unknown): string {
  if (reason instanceof ApiRequestError) {
    if (reason.code === "provider_rate_limited") {
      return reason.nextAction === "configure_openalex_api_key"
        ? "OpenAlex 当前需要 API Key，请配置 OPENALEX_API_KEY 后再试。"
        : "OpenAlex 已触发限流，请等待重置后再试。";
    }
    if (reason.code === "provider_auth_required") return "OpenAlex 当前需要 API Key，请配置 OPENALEX_API_KEY 后再试，或切换到 arXiv。";
    if (reason.code === "provider_unavailable") return "论文发现服务暂时不可用，请稍后重试。";
    if (reason.code === "outline_not_found") return "当前工作区还没有报告大纲。";
    if (reason.code === "outline_unavailable") return "请先选择并处理至少一篇论文，直到证据状态变为“证据就绪”。";
    if (reason.code === "invalid_outline") return "大纲版本已变化，请刷新后再保存。";
    if (reason.code === "paper_not_found") return "找不到这篇论文，它可能已不在当前工作区。";
    return "请求失败，请检查服务状态后重试。";
  }
  return "请求失败，请检查服务状态后重试。";
}

function paperFailureMessage(paper: ResearchPaper): string | null {
  if (paper.evidence_readiness === "awaiting_authorised_file") {
    return "没有可自动下载的公开 PDF，请上传已授权 PDF。";
  }
  if (paper.evidence_readiness === "failed") {
    const detail = localizeFailureReason(paper.failure_message);
    return detail ? `论文处理失败：${detail}` : "论文处理失败，可以重试或上传已授权 PDF。";
  }
  return null;
}

function localizeFailureReason(reason: string | null): string | null {
  if (!reason) return null;
  const translations: Array<[string, string]> = [
    ["All public PDF sources failed:", "所有公开 PDF 来源均失败："],
    ["The selected public URL did not return a valid PDF.", "所选公开地址返回的不是有效 PDF。"],
    ["The selected public URL did not return a PDF.", "所选公开地址返回的不是 PDF。"],
    ["The public PDF URL did not return a successful response.", "公开 PDF 地址没有返回成功响应。"],
    ["The public PDF could not be downloaded; retry later.", "公开 PDF 下载失败，请稍后重试。"],
    ["The public PDF redirected too many times.", "公开 PDF 重定向次数过多。"],
    ["The candidate does not provide a valid public PDF URL.", "候选论文没有提供有效的公开 PDF 地址。"],
    ["The public PDF could not be saved to the workspace.", "公开 PDF 无法保存到工作区。"],
    ["No public PDF source was available.", "没有可用的公开 PDF 来源。"],
    ["The selected PDF exceeds the workspace import limit.", "所选 PDF 超过工作区导入大小限制。"],
    ["PDF parsing failed. Retry the import or provide another authorised PDF.", "PDF 解析失败，请重试导入或提供其他已授权 PDF。"],
  ];
  return translations.reduce((value, [english, chinese]) => value.replace(english, chinese), reason)
    .replace(/The public PDF[^.]*\./g, "公开 PDF 来源处理失败。")
    .replace(/The selected public URL[^.]*\./g, "所选公开地址处理失败。")
    .replace(/^[A-Z][^:]* failed:\s*/g, "处理失败：")
    || "未分类的处理失败，请重试或上传已授权 PDF。";
}

function operationErrorMessage(operation: WorkspaceOperation): string | null {
  if (!operation.error_message) return null;
  return operation.error_category === "provider_rate_limited"
    ? "服务触发限流，请等待重置后重试。"
    : "操作失败，可以点击下方按钮重试。";
}

function App() {
  const [workspaces, setWorkspaces] = useState<ResearchWorkspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [workspace, setWorkspace] = useState<ResearchWorkspace | null>(null);
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

  const refreshWorkspaces = useCallback(async () => {
    const result = await listWorkspaces();
    setWorkspaces(result);
    if (!workspaceId && result[0]) setWorkspaceId(result[0].id);
  }, [workspaceId]);

  const refreshWorkspace = useCallback(async (id: string) => {
    const result = await getWorkspace(id);
    setWorkspace(result);
    setDiscoveryQuery((current) => current || result.topic);
    setWorkspaces((current) => current.map((item) => (item.id === id ? result : item)));
  }, []);

  useEffect(() => {
    const outline = workspace?.outline;
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
  }, [workspace?.id, workspace?.outline?.id, workspace?.outline?.status, workspace?.outline?.updated_at]);

  useEffect(() => {
    void refreshWorkspaces().catch((reason: unknown) => setError(localizeError(reason)));
  }, [refreshWorkspaces]);

  useEffect(() => {
    if (!workspaceId) {
      setWorkspace(null);
      return;
    }
    void refreshWorkspace(workspaceId).catch((reason: unknown) => setError(localizeError(reason)));
  }, [refreshWorkspace, workspaceId]);

  const activeOperation = Boolean(workspace?.operations.some((operation) => operation.status === "queued" || operation.status === "running"));
  const outlineGenerating = Boolean(workspace?.operations.some(
    (operation) => operation.operation_type === "generate_outline" && (operation.status === "queued" || operation.status === "running"),
  ));

  useEffect(() => {
    if (!workspaceId || !activeOperation) return undefined;
    const timer = window.setInterval(() => {
      void refreshWorkspace(workspaceId).catch((reason: unknown) => setError(localizeError(reason)));
    }, 800);
    return () => window.clearInterval(timer);
  }, [activeOperation, refreshWorkspace, workspaceId]);

  const selectedPapers = useMemo(() => workspace?.papers.filter((paper) => paper.selected) ?? [], [workspace]);
  const candidatePapers = useMemo(
    () => workspace?.papers.filter((paper) => paper.source_kind === "discovery" && !paper.selected && !paper.dismissed) ?? [],
    [workspace],
  );
  const dismissedPapers = useMemo(
    () => workspace?.papers.filter((paper) => paper.source_kind === "discovery" && !paper.selected && paper.dismissed) ?? [],
    [workspace],
  );
  const unselectedPapers = useMemo(
    () => workspace?.papers.filter((paper) => paper.source_kind === "upload" && !paper.selected) ?? [],
    [workspace],
  );
  const readyCount = selectedPapers.filter((paper) => paper.evidence_eligible).length;

  async function runAction(key: string, action: () => Promise<void>) {
    setBusyKey(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      if (workspaceId) await refreshWorkspace(workspaceId);
    } catch (reason: unknown) {
      setError(localizeError(reason));
    } finally {
      setBusyKey(null);
    }
  }

  function addOperation(operation: WorkspaceOperation | null) {
    if (!operation) return;
    setWorkspace((current) => current ? {
      ...current,
      operations: [operation, ...current.operations.filter((item) => item.id !== operation.id)],
    } : current);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newTopic.trim()) return;
    await runAction("create-workspace", async () => {
      const result = await createWorkspace(newTopic, newLanguage);
      setNewTopic("");
      setWorkspaceId(result.id);
      setWorkspace(result);
      setWorkspaces((current) => [...current, result]);
      setDiscoveryQuery(result.topic);
      setNotice("工作区已创建，可以开始准备证据集合。");
    });
  }

  async function handleDiscover(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspace || !discoveryQuery.trim()) return;
    await runAction("discover", async () => {
      const result = await discoverPapers(workspace.id, discoveryQuery, provider);
      setDiscovery(result);
      if (result.status === "succeeded") {
        setNotice(`发现 ${result.candidates.length} 篇候选论文。候选论文不会自动成为证据。`);
      } else if (result.status === "empty") {
        setNotice("没有找到新的候选论文。");
      } else if (result.provider === "openalex" && result.next_action === "configure_openalex_api_key") {
        setError("OpenAlex 当前需要 API Key，请配置 OPENALEX_API_KEY；也可以切换到 arXiv。");
      } else if (result.provider === "openalex" && result.retry_after_seconds) {
        setError(`OpenAlex 已限流，请约 ${result.retry_after_seconds} 秒后再试，或切换到 arXiv。`);
      } else {
        setError("论文发现暂时失败，可以稍后重试或切换来源。");
      }
    });
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>, candidateId?: string) {
    event.preventDefault();
    const file = candidateId ? candidateFiles[candidateId] : uploadFile;
    if (!workspace || !file) return;
    await runAction(candidateId ? `upload-${candidateId}` : "upload-paper", async () => {
      const result = await uploadPaper(workspace.id, file, candidateId);
      addOperation(result.operation);
      if (candidateId) setCandidateFiles((current) => ({ ...current, [candidateId]: null }));
      else setUploadFile(null);
      setNotice("文件已接收，正在后台处理；操作状态会持续更新。");
    });
  }

  async function handleImport(paper: ResearchPaper) {
    if (!workspace) return;
    await runAction(`import-${paper.id}`, async () => {
      const result = await importPaper(workspace.id, paper.id);
      addOperation(result.operation);
      setNotice(result.operation ? "公开 PDF 已提交导入，论文已进入已选论文。" : "没有可自动导入的公开 PDF，请上传已授权文件。");
    });
  }

  async function handleRetry(paper: ResearchPaper) {
    if (!workspace) return;
    await runAction(`retry-${paper.id}`, async () => {
      const result = await retryPaper(workspace.id, paper.id);
      addOperation(result.operation);
      setNotice("已创建新的处理尝试，旧的失败记录仍会保留。");
    });
  }

  async function handleDismiss(paper: ResearchPaper) {
    if (!workspace) return;
    await runAction(`dismiss-${paper.id}`, async () => {
      await dismissPaper(workspace.id, paper.id);
      setNotice("候选论文已忽略；后续检索不会再次展示它。可在“已忽略候选”中恢复。");
    });
  }

  async function handleRestorePaper(paper: ResearchPaper) {
    if (!workspace) return;
    await runAction(`restore-${paper.id}`, async () => {
      await restorePaper(workspace.id, paper.id);
      setNotice("候选论文已恢复，可以重新审阅。");
    });
  }

  async function handleGenerateOutline() {
    if (!workspace) return;
    await runAction("generate-outline", async () => {
      const operation = await generateOutline(workspace.id);
      addOperation(operation);
      setNotice("大纲生成任务已排队，完成后可以编辑并审批。");
    });
  }

  async function handleRetryOutline(operation: WorkspaceOperation) {
    if (!workspace) return;
    await runAction(`retry-${operation.id}`, async () => {
      const retry = await retryOperation(operation.id);
      addOperation(retry);
      setNotice("大纲生成已重新排队。");
    });
  }

  async function handleSaveOutline() {
    if (!workspace || !outlineDraft) return;
    await runAction("save-outline", async () => {
      await saveOutline(workspace.id, outlineDraft);
      setNotice("大纲草稿已保存；已审批版本不会被覆盖。");
    });
  }

  async function handleApproveOutline() {
    if (!workspace || !outlineDraft) return;
    await runAction("approve-outline", async () => {
      await approveOutline(workspace.id, outlineDraft.id);
      setNotice("当前大纲修订已审批，可用于后续报告生成。");
    });
  }

  async function handleOpenHistory() {
    if (!workspace) return;
    await runAction("outline-history", async () => {
      const revisions = await listOutlineRevisions(workspace.id);
      setOutlineHistory(revisions);
      setHistoryOpen(true);
    });
  }

  async function handleRestoreOutline(revision: ReportOutline) {
    if (!workspace) return;
    await runAction(`restore-outline-${revision.id}`, async () => {
      const restored = await restoreOutlineRevision(workspace.id, revision.id);
      setOutlineDraft({ ...restored, sections: restored.sections.map((section) => ({ ...section })) });
      setOutlineHistory(null);
      setHistoryOpen(false);
      setNotice(`已从修订 ${revision.revision_number} 创建新的草稿修订。`);
    });
  }

  function updateOutlineDraft(update: (outline: ReportOutline) => ReportOutline) {
    setOutlineDraft((current) => current ? update(current) : current);
  }

  function addOutlineSection() {
    updateOutlineDraft((current) => ({
      ...current,
      sections: [...current.sections, {
        id: `section-${Date.now()}`,
        title: "新章节",
        description: "",
      }],
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

  if (!workspace && !workspaces.length) {
    return (
      <div className="empty-shell">
        <div className="empty-card">
          <p className="eyebrow">PAPERRAG / 研究工作区</p>
          <h1>把阅读任务变成可追溯的工作区。</h1>
          <p className="muted">先定义研究主题，再上传或发现论文。只有你明确选入并处理就绪的论文，才能成为报告证据。</p>
          <WorkspaceForm topic={newTopic} language={newLanguage} submitLabel="创建第一个工作区" onTopicChange={setNewTopic} onLanguageChange={setNewLanguage} onSubmit={handleCreate} busy={busyKey === "create-workspace"} />
          {error && <p className="error-message">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">PAPERRAG / 研究工作区</p>
          <h1>研究论文，证据先行。</h1>
        </div>
        <div className="workspace-switcher">
          <label htmlFor="workspace-select">当前工作区</label>
          <select id="workspace-select" data-testid="workspace-select" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)}>
            {workspaces.map((item) => <option value={item.id} key={item.id}>{item.topic}</option>)}
          </select>
        </div>
      </header>

      <main className="workspace-layout">
        <aside className="panel paper-boundary">
          <PanelHeading eyebrow="01 / 证据边界" title="论文集合" />
          <div className="boundary-summary">
            <strong>{readyCount}</strong>
            <span>篇证据就绪</span>
            <small>已选论文：{selectedPapers.length} · 候选：{candidatePapers.length}</small>
          </div>
          <section>
            <SectionLabel label="已选论文" detail="可供后续工作使用" />
            {selectedPapers.length ? selectedPapers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} selected onImport={paper.evidence_readiness === "unavailable" ? () => void handleImport(paper) : undefined} onRemove={() => void runAction(`remove-${paper.id}`, async () => { if (workspace) await removePaper(workspace.id, paper.id); setNotice("论文已移出当前证据边界，历史记录仍保留。"); })} onRetry={() => void handleRetry(paper)} onUpload={(file) => setCandidateFiles((current) => ({ ...current, [paper.id]: file }))} candidateFile={candidateFiles[paper.id] ?? null} onCandidateUpload={(event) => void handleUpload(event, paper.id)} busyKey={busyKey} />
            )) : <EmptyState text="还没有已选论文。" />}
          </section>
          {unselectedPapers.length > 0 && <section><SectionLabel label="未选入的上传论文" detail="不会影响报告" />{unselectedPapers.map((paper) => <PaperCard key={paper.id} paper={paper} onSelect={() => void runAction(`select-${paper.id}`, async () => { if (workspace) await selectPaper(workspace.id, paper.id); setNotice("论文已加入已选论文。"); })} busyKey={busyKey} />)}</section>}
          <section>
            <SectionLabel label="候选论文" detail="发现结果，尚未纳入证据" />
            {candidatePapers.length ? candidatePapers.map((paper) => <PaperCard key={paper.id} paper={paper} candidate onImport={() => void handleImport(paper)} onSelect={() => void runAction(`select-${paper.id}`, async () => { if (workspace) await selectPaper(workspace.id, paper.id); setNotice("候选论文已选入，但仍需处理就绪后才能成为证据。"); })} onDismiss={() => void handleDismiss(paper)} onUpload={(file) => setCandidateFiles((current) => ({ ...current, [paper.id]: file }))} candidateFile={candidateFiles[paper.id] ?? null} onCandidateUpload={(event) => void handleUpload(event, paper.id)} busyKey={busyKey} />) : <EmptyState text="运行一次主题发现，这里会出现候选论文。" />}
          </section>
          {dismissedPapers.length > 0 && <section className="dismissed-section"><SectionLabel label="已忽略候选" detail="可恢复" />{dismissedPapers.map((paper) => <PaperCard key={paper.id} paper={paper} dismissed onRestore={() => void handleRestorePaper(paper)} busyKey={busyKey} />)}</section>}
        </aside>

        <section className="panel preparation-panel">
          <PanelHeading eyebrow="02 / 工作准备" title={workspace?.topic ?? "工作区准备"} />
          {workspace && <>
            <div className="topic-block"><span className="status-dot" /><div><strong>{workspace.state === "active" ? "工作区已激活" : "工作区设置中"}</strong><p>报告语言：{workspace.report_language === "zh" ? "中文" : "英文"}。先把已选论文准备好，再生成和审批报告大纲。</p></div></div>
            <div className="card-block"><SectionLabel label="上传已授权的研究论文" detail="仅接受 PDF" /><form className="upload-row" onSubmit={(event) => void handleUpload(event)}><label className="file-picker"><input data-testid="upload-paper" type="file" accept="application/pdf,.pdf" onChange={(event: ChangeEvent<HTMLInputElement>) => setUploadFile(event.target.files?.[0] ?? null)} /><span>{uploadFile?.name ?? "选择 PDF 文件"}</span></label><button type="submit" disabled={!uploadFile || busyKey === "upload-paper"}>{busyKey === "upload-paper" ? "提交中…" : "上传并处理"}</button></form><p className="helper-text">直接上传的论文会进入已选论文；解析或索引失败时可以在左侧重试。</p></div>
            <div className="card-block"><SectionLabel label="发现开放论文" detail="来源：OpenAlex / arXiv" /><form className="discovery-form" onSubmit={(event) => void handleDiscover(event)}><input data-testid="discovery-query" value={discoveryQuery} onChange={(event) => setDiscoveryQuery(event.target.value)} placeholder="例如：RAG 证据溯源" /><select value={provider} onChange={(event) => setProvider(event.target.value as "openalex" | "arxiv")} aria-label="发现来源"><option value="openalex">OpenAlex</option><option value="arxiv">arXiv</option></select><button data-testid="discovery-submit" type="submit" disabled={!discoveryQuery.trim() || busyKey === "discover"}>{busyKey === "discover" ? "搜索中…" : "搜索候选"}</button></form>{discovery && <DiscoverySummary discovery={discovery} onSwitchToArxiv={() => setProvider("arxiv")} />}</div>
            <div className="readiness-callout"><span className="callout-icon">→</span><div><strong>证据边界是显式的</strong><p>候选论文只提供元数据。只有已选且状态为“证据就绪”的论文，才会进入后续检索、生成和引用。</p></div></div>
            <OutlineEditor outline={outlineDraft} readyCount={readyCount} generating={outlineGenerating} busyKey={busyKey} onGenerate={() => void handleGenerateOutline()} onSave={() => void handleSaveOutline()} onApprove={() => void handleApproveOutline()} onChange={updateOutlineDraft} onAddSection={addOutlineSection} onMoveSection={moveOutlineSection} onOpenHistory={() => void handleOpenHistory()} />
            {historyOpen && outlineHistory && <OutlineHistory revisions={outlineHistory} currentId={outlineDraft?.id ?? null} busyKey={busyKey} onClose={() => setHistoryOpen(false)} onRestore={(revision) => void handleRestoreOutline(revision)} />}
          </>}
          {notice && <p className="notice-message">{notice}</p>}
          {error && <p className="error-message">{error}</p>}
        </section>

        <aside className="panel activity-panel">
          <PanelHeading eyebrow="03 / 持久化活动" title="处理状态" />
          <p className="muted">这些状态来自持久化工作区操作。刷新页面后仍会保留。</p>
          <section className="activity-list" aria-live="polite">{workspace?.operations.length ? workspace.operations.map((operation) => <OperationCard key={operation.id} operation={operation} papers={workspace.papers} onRetry={(paper) => void handleRetry(paper)} onRetryOutline={(item) => void handleRetryOutline(item)} busyKey={busyKey} />) : <EmptyState text="上传或导入论文后，操作记录会出现在这里。" />}</section>
          <div className="new-workspace-block"><SectionLabel label="另建一个工作区" detail="单用户部署" /><WorkspaceForm compact topic={newTopic} language={newLanguage} submitLabel="创建" onTopicChange={setNewTopic} onLanguageChange={setNewLanguage} onSubmit={handleCreate} busy={busyKey === "create-workspace"} /></div>
        </aside>
      </main>
    </div>
  );
}

function OutlineEditor({ outline, readyCount, generating, busyKey, onGenerate, onSave, onApprove, onChange, onAddSection, onMoveSection, onOpenHistory }: { outline: ReportOutline | null; readyCount: number; generating: boolean; busyKey: string | null; onGenerate: () => void; onSave: () => void; onApprove: () => void; onChange: (update: (outline: ReportOutline) => ReportOutline) => void; onAddSection: () => void; onMoveSection: (index: number, offset: -1 | 1) => void; onOpenHistory: () => void }) {
  if (!outline) return <div className="outline-editor card-block" data-testid="outline-editor"><SectionLabel label="报告大纲" detail="先审批结构，再生成报告" /><p className="helper-text">{readyCount > 0 ? "当前已有可用证据，可以生成默认大纲。" : "请先选择并处理至少一篇已选论文，直到状态变为“证据就绪”。"}</p><button data-testid="outline-generate" type="button" onClick={onGenerate} disabled={readyCount === 0 || generating || busyKey === "generate-outline"}>{busyKey === "generate-outline" ? "生成中…" : "生成大纲"}</button></div>;
  return <div className="outline-editor card-block" data-testid="outline-editor">
    <div className="outline-heading"><SectionLabel label="报告大纲" detail={`修订 ${outline.revision_number}`} /><div className="outline-heading-actions"><span className={`badge badge-${outline.status}`} data-testid="outline-status">{outline.status === "approved" ? "已审批" : "草稿"}</span><button type="button" className="button-quiet" data-testid="outline-history" onClick={onOpenHistory}>历史版本</button></div></div>
    <label className="outline-field">标题<input data-testid="outline-title" value={outline.title} onChange={(event) => onChange((current) => ({ ...current, title: event.target.value }))} /></label>
    <label className="outline-field">研究问题<textarea data-testid="outline-research-question" rows={3} value={outline.research_question} onChange={(event) => onChange((current) => ({ ...current, research_question: event.target.value }))} /></label>
    <div className="outline-section-list">{outline.sections.map((section, index) => <article className="outline-section" data-testid="outline-section" key={section.id}><div className="outline-section-toolbar"><span>{index + 1}</span><button type="button" aria-label="上移章节" onClick={() => onMoveSection(index, -1)} disabled={index === 0}>↑</button><button type="button" aria-label="下移章节" onClick={() => onMoveSection(index, 1)} disabled={index === outline.sections.length - 1}>↓</button><button type="button" className="button-quiet" onClick={() => onChange((current) => ({ ...current, sections: current.sections.filter((item) => item.id !== section.id) }))} disabled={outline.sections.length <= 1}>删除</button></div><input data-testid={`outline-section-title-${section.id}`} value={section.title} aria-label={`第 ${index + 1} 章节标题`} onChange={(event) => onChange((current) => ({ ...current, sections: current.sections.map((item) => item.id === section.id ? { ...item, title: event.target.value } : item) }))} /><textarea value={section.description} aria-label={`第 ${index + 1} 章节说明`} rows={2} onChange={(event) => onChange((current) => ({ ...current, sections: current.sections.map((item) => item.id === section.id ? { ...item, description: event.target.value } : item) }))} /></article>)}</div>
    <div className="outline-actions"><button type="button" className="button-quiet" data-testid="outline-add-section" onClick={onAddSection}>添加章节</button><button type="button" data-testid="outline-save" onClick={onSave} disabled={busyKey === "save-outline"}>{busyKey === "save-outline" ? "保存中…" : "保存草稿"}</button>{outline.status === "draft" && <button type="button" data-testid="outline-approve" onClick={onApprove} disabled={busyKey === "approve-outline"}>{busyKey === "approve-outline" ? "审批中…" : "审批此修订"}</button>}</div>
    <p className="helper-text">{outline.status === "approved" ? "此修订不可变。保存编辑会创建新的草稿修订。" : "可以编辑、排序、添加或删除章节，然后审批此修订。"}</p>
  </div>;
}

function OutlineHistory({ revisions, currentId, busyKey, onClose, onRestore }: { revisions: ReportOutline[]; currentId: string | null; busyKey: string | null; onClose: () => void; onRestore: (revision: ReportOutline) => void }) {
  return <div className="outline-history-backdrop" data-testid="outline-history-panel" role="dialog" aria-modal="true" aria-label="大纲历史"><aside className="outline-history-drawer"><div className="outline-heading"><SectionLabel label="大纲历史" detail={`${revisions.length} 个修订`} /><button type="button" className="button-quiet" onClick={onClose}>关闭</button></div>{revisions.length ? <div className="history-list">{revisions.map((revision) => <article className="history-item" data-testid="outline-history-item" key={revision.id}><div className="history-item-heading"><strong>修订 {revision.revision_number}</strong><span className={`badge badge-${revision.status}`}>{revision.status === "approved" ? "已审批" : "草稿"}</span></div><p>{revision.title}</p><p className="history-summary"><strong>研究问题：</strong>{revision.research_question}</p><ul className="history-sections">{revision.sections.map((section) => <li key={section.id}><strong>{section.title}</strong>{section.description && `：${section.description}`}</li>)}</ul><small>{revision.updated_at ? new Date(revision.updated_at).toLocaleString("zh-CN") : "时间未知"}</small><div className="history-item-actions">{revision.id === currentId ? <span className="muted">当前修订</span> : <button type="button" onClick={() => void onRestore(revision)} disabled={busyKey === `restore-outline-${revision.id}`}>{busyKey === `restore-outline-${revision.id}` ? "恢复中…" : "恢复为新草稿"}</button>}</div></article>)}</div> : <EmptyState text="还没有历史修订。" />}</aside></div>;
}

function WorkspaceForm({ compact = false, topic, language, submitLabel, onTopicChange, onLanguageChange, onSubmit, busy }: { compact?: boolean; topic: string; language: ReportLanguage; submitLabel: string; onTopicChange: (value: string) => void; onLanguageChange: (value: ReportLanguage) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; busy: boolean }) {
  if (compact) return <form className="compact-create-form" onSubmit={onSubmit}><input data-testid="workspace-topic" value={topic} onChange={(event) => onTopicChange(event.target.value)} placeholder="新的研究主题" /><div className="inline-form"><select value={language} onChange={(event) => onLanguageChange(event.target.value as ReportLanguage)} aria-label="新工作区报告语言"><option value="zh">中文报告</option><option value="en">英文报告</option></select><button data-testid="workspace-create" type="submit" disabled={!topic.trim() || busy}>{busy ? "创建中…" : submitLabel}</button></div></form>;
  return <form className="create-form" onSubmit={onSubmit}><label>研究主题<input data-testid="workspace-topic" value={topic} onChange={(event) => onTopicChange(event.target.value)} placeholder="例如：RAG 证据溯源" autoFocus /></label><label>报告语言<select value={language} onChange={(event) => onLanguageChange(event.target.value as ReportLanguage)}><option value="zh">中文</option><option value="en">英文</option></select></label><button data-testid="workspace-create" type="submit" disabled={!topic.trim() || busy}>{busy ? "创建中…" : submitLabel}</button></form>;
}

function PaperCard({ paper, selected = false, candidate = false, dismissed = false, onImport, onSelect, onRemove, onDismiss, onRestore, onRetry, onUpload, candidateFile, onCandidateUpload, busyKey }: { paper: ResearchPaper; selected?: boolean; candidate?: boolean; dismissed?: boolean; onImport?: () => void; onSelect?: () => void; onRemove?: () => void; onDismiss?: () => void; onRestore?: () => void; onRetry?: () => void; onUpload?: (file: File) => void; candidateFile?: File | null; onCandidateUpload?: (event: FormEvent<HTMLFormElement>) => void; busyKey: string | null }) {
  const importKey = `import-${paper.id}`;
  const selectKey = `select-${paper.id}`;
  const removeKey = `remove-${paper.id}`;
  const dismissKey = `dismiss-${paper.id}`;
  const restoreKey = `restore-${paper.id}`;
  const retryKey = `retry-${paper.id}`;
  const uploadKey = `upload-${paper.id}`;
  const needsAuthorisedFile = paper.evidence_readiness === "awaiting_authorised_file" || paper.evidence_readiness === "failed";
  const hasPdf = Boolean(paper.pdf_urls?.length || paper.pdf_url);
  return <article className={`paper-card ${paper.evidence_eligible ? "paper-ready" : ""}`} data-testid={dismissed ? "paper-dismissed" : candidate ? "paper-candidate" : selected ? "paper-selected" : "paper-unselected"}><div className="paper-card-heading"><div><h3>{paper.title}</h3><p>{paper.authors.slice(0, 3).join(" · ") || "作者信息未提供"}{paper.year && ` · ${paper.year}`}</p></div>{paper.evidence_eligible ? <span className="badge badge-ready" data-testid="paper-evidence-eligible">证据可用</span> : <span className={`badge badge-${paper.evidence_readiness}`}>{readinessLabels[paper.evidence_readiness]}</span>}</div>{paper.venue && <p className="paper-venue">{paper.venue}</p>}{paper.abstract && <p className="paper-abstract">{paper.abstract}</p>}{paper.source_url && <a className="paper-link" href={paper.source_url} target="_blank" rel="noreferrer">查看来源 →</a>}{!dismissed && paperFailureMessage(paper) && <p className="paper-failure">{paperFailureMessage(paper)}</p>}<div className="paper-actions">{candidate && onImport && <button data-testid={`import-paper-${paper.id}`} type="button" onClick={onImport} disabled={busyKey === importKey}>{busyKey === importKey ? "提交中…" : hasPdf && paper.is_open_access !== false ? "尝试导入 PDF" : "准备授权文件"}</button>}{candidate && onSelect && <button className="button-quiet" data-testid={`select-paper-${paper.id}`} type="button" onClick={onSelect} disabled={busyKey === selectKey}>先选入</button>}{candidate && onDismiss && <button className="button-quiet" data-testid={`dismiss-paper-${paper.id}`} type="button" onClick={onDismiss} disabled={busyKey === dismissKey}>忽略此论文</button>}{!candidate && !dismissed && onSelect && <button type="button" onClick={onSelect} disabled={busyKey === selectKey}>{busyKey === selectKey ? "处理中…" : "加入已选论文"}</button>}{selected && onRemove && <button className="button-quiet" data-testid={`remove-paper-${paper.id}`} type="button" onClick={onRemove} disabled={busyKey === removeKey}>移出证据边界</button>}{dismissed && onRestore && <button type="button" data-testid={`restore-paper-${paper.id}`} onClick={onRestore} disabled={busyKey === restoreKey}>{busyKey === restoreKey ? "恢复中…" : "恢复候选"}</button>}{paper.retryable && onRetry && <button className="button-warning" data-testid={`retry-paper-${paper.id}`} type="button" onClick={onRetry} disabled={busyKey === retryKey}>{busyKey === retryKey ? "重试中…" : "重试处理"}</button>}</div>{needsAuthorisedFile && onCandidateUpload && <form className="authorised-upload" onSubmit={onCandidateUpload}><label className="file-picker compact"><input data-testid={`authorised-upload-${paper.id}`} type="file" accept="application/pdf,.pdf" onChange={(event: ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0]; if (file && onUpload) onUpload(file); }} /><span>{candidateFile?.name ?? "选择已授权 PDF"}</span></label><button type="submit" disabled={!candidateFile || busyKey === uploadKey}>{busyKey === uploadKey ? "提交中…" : "上传授权文件"}</button></form>}</article>;
}

function OperationCard({ operation, papers, onRetry, onRetryOutline, busyKey }: { operation: WorkspaceOperation; papers: ResearchPaper[]; onRetry: (paper: ResearchPaper) => void; onRetryOutline: (operation: WorkspaceOperation) => void; busyKey: string | null }) {
  const paper = papers.find((item) => item.id === operation.paper_id);
  const percent = operation.total_work ? Math.round((operation.completed_work / operation.total_work) * 100) : 0;
  const active = operation.status === "queued" || operation.status === "running";
  const retryKey = `retry-${operation.id}`;
  return <article className="operation-card" data-testid="operation-status"><div className="operation-heading"><strong>{operationLabels[operation.operation_type] || "工作区操作"}</strong><span className={`operation-status status-${operation.status}`}>{operationStatusLabels[operation.status]}</span></div><p className="operation-paper">{paper?.title || "工作区操作"}</p><div className="progress-track"><span style={{ width: `${active ? Math.max(percent, operation.phase === "importing" ? 10 : 35) : percent}%` }} /></div><div className="operation-meta"><span>{phaseLabels[operation.phase] || operation.phase}</span><span>{operation.completed_work}/{operation.total_work}</span></div>{operationErrorMessage(operation) && <p className="operation-error">{operationErrorMessage(operation)}</p>}{(operation.retry_action || operation.status === "failed" || operation.status === "interrupted") && operation.operation_type === "generate_outline" && <button className="button-warning full-width" type="button" onClick={() => onRetryOutline(operation)} disabled={busyKey === retryKey}>重试大纲生成</button>}{(operation.retry_action || operation.status === "failed" || operation.status === "interrupted") && paper && <button className="button-warning full-width" type="button" onClick={() => onRetry(paper)} disabled={busyKey === `retry-${paper.id}`}>恢复此操作</button>}</article>;
}

function DiscoverySummary({ discovery, onSwitchToArxiv }: { discovery: DiscoveryResponse; onSwitchToArxiv: () => void }) {
  const failed = discovery.status === "retryable_error" || discovery.status === "failed";
  const canSwitchToArxiv = discovery.provider === "openalex";
  const message = failed && canSwitchToArxiv && discovery.next_action === "configure_openalex_api_key"
    ? "OpenAlex 需要配置 OPENALEX_API_KEY；也可以切换到 arXiv。"
    : failed && discovery.retry_after_seconds
      ? `服务正在限流，预计 ${discovery.retry_after_seconds} 秒后可以重试。`
      : failed
        ? "论文发现暂时失败，可以手动重试或切换来源。"
        : "候选论文已加入左侧，可逐篇审阅。";
  return <div className={`discovery-result discovery-${discovery.status}`} data-testid="discovery-results"><strong>{discovery.status === "succeeded" ? `已保存 ${discovery.candidates.length} 个候选` : discovery.status === "empty" ? "没有候选结果" : "发现失败"}</strong><span>{message}</span>{failed && canSwitchToArxiv && <button type="button" className="button-quiet" onClick={onSwitchToArxiv}>切换到 arXiv</button>}</div>;
}

function PanelHeading({ eyebrow, title }: { eyebrow: string; title: string }) { return <div className="panel-heading"><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>; }
function SectionLabel({ label, detail }: { label: string; detail: string }) { return <div className="section-label"><strong>{label}</strong><span>{detail}</span></div>; }
function EmptyState({ text }: { text: string }) { return <p className="empty-state">{text}</p>; }

createRoot(document.getElementById("root")!).render(<App />);
