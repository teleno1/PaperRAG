import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import {
  createWorkspace,
  discoverPapers,
  getWorkspace,
  importPaper,
  listWorkspaces,
  removePaper,
  retryPaper,
  selectPaper,
  uploadPaper,
} from "./api";
import type {
  DiscoveryResponse,
  EvidenceReadiness,
  ResearchPaper,
  ResearchWorkspace,
  ReportLanguage,
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
  unavailable: "暂不可用",
};

const operationLabels: Record<string, string> = {
  import_paper: "上传论文",
  import_authorised_paper: "上传授权文件",
  import_discovered_paper: "导入开放论文",
  retry_paper_import: "重试论文处理",
};

function App() {
  const [workspaces, setWorkspaces] = useState<ResearchWorkspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [workspace, setWorkspace] = useState<ResearchWorkspace | null>(null);
  const [discovery, setDiscovery] = useState<DiscoveryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [topic, setTopic] = useState("");
  const [language, setLanguage] = useState<ReportLanguage>("zh");
  const [newTopic, setNewTopic] = useState("");
  const [newLanguage, setNewLanguage] = useState<ReportLanguage>("zh");
  const [discoveryQuery, setDiscoveryQuery] = useState("");
  const [provider, setProvider] = useState<"openalex" | "arxiv">("openalex");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [candidateFiles, setCandidateFiles] = useState<Record<string, File | null>>({});

  const refreshWorkspaces = useCallback(async () => {
    const result = await listWorkspaces();
    setWorkspaces(result);
    if (!workspaceId && result[0]) setWorkspaceId(result[0].id);
  }, [workspaceId]);

  const refreshWorkspace = useCallback(async (id: string) => {
    const result = await getWorkspace(id);
    setWorkspace(result);
    setTopic(result.topic);
    setLanguage(result.report_language);
    setDiscoveryQuery((current) => current || result.topic);
    setWorkspaces((current) => current.map((item) => (item.id === id ? result : item)));
  }, []);

  useEffect(() => {
    void refreshWorkspaces().catch((reason: unknown) => setError(errorMessage(reason)));
  }, [refreshWorkspaces]);

  useEffect(() => {
    if (!workspaceId) {
      setWorkspace(null);
      return;
    }
    void refreshWorkspace(workspaceId).catch((reason: unknown) => setError(errorMessage(reason)));
  }, [refreshWorkspace, workspaceId]);

  const hasActiveOperation = Boolean(
    workspace?.operations.some((operation) => operation.status === "queued" || operation.status === "running"),
  );

  useEffect(() => {
    if (!workspaceId || !hasActiveOperation) return undefined;
    const timer = window.setInterval(() => {
      void refreshWorkspace(workspaceId).catch((reason: unknown) => setError(errorMessage(reason)));
    }, 800);
    return () => window.clearInterval(timer);
  }, [hasActiveOperation, refreshWorkspace, workspaceId]);

  const selectedPapers = useMemo(() => workspace?.papers.filter((paper) => paper.selected) ?? [], [workspace]);
  const candidatePapers = useMemo(
    () => workspace?.papers.filter((paper) => paper.source_kind === "discovery" && !paper.selected) ?? [],
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
      setError(errorMessage(reason));
    } finally {
      setBusyKey(null);
    }
  }

  function addOperation(operation: WorkspaceOperation | null) {
    if (!operation) return;
    setWorkspace((current) =>
      current
        ? {
            ...current,
            operations: [operation, ...current.operations.filter((item) => item.id !== operation.id)],
          }
        : current,
    );
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
      setNotice(
        result.status === "succeeded"
          ? `发现 ${result.candidates.length} 篇候选论文。候选论文不会自动成为证据。`
          : result.error_message || (result.status === "empty" ? "没有找到候选论文。" : "发现暂时失败，可稍后重试。"),
      );
    });
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>, candidateId?: string) {
    event.preventDefault();
    const file = candidateId ? candidateFiles[candidateId] : uploadFile;
    if (!workspace || !file) return;
    await runAction(candidateId ? `upload-${candidateId}` : "upload-paper", async () => {
      const result = await uploadPaper(workspace.id, file, candidateId);
      addOperation(result.operation);
      if (candidateId) {
        setCandidateFiles((current) => ({ ...current, [candidateId]: null }));
      } else {
        setUploadFile(null);
      }
      setNotice("文件已接收，正在后台处理；页面会持续显示可恢复状态。 ");
    });
  }

  async function handleImport(paper: ResearchPaper) {
    if (!workspace) return;
    await runAction(`import-${paper.id}`, async () => {
      const result = await importPaper(workspace.id, paper.id);
      addOperation(result.operation);
      setNotice(
        result.operation
          ? "开放 PDF 已提交导入，候选论文现在位于 Selected Papers 中。"
          : "该论文没有可自动导入的公开 PDF，请上传你已获授权的文件。",
      );
    });
  }

  async function handleRetry(paper: ResearchPaper) {
    if (!workspace) return;
    await runAction(`retry-${paper.id}`, async () => {
      const result = await retryPaper(workspace.id, paper.id);
      addOperation(result.operation);
      setNotice("已创建新的处理尝试，旧的失败记录仍会保留。 ");
    });
  }

  if (!workspace && !workspaces.length) {
    return (
      <div className="empty-shell">
        <div className="empty-card">
          <p className="eyebrow">PAPERRAG / RESEARCH WORKSPACE</p>
          <h1>把阅读任务变成可追溯的工作区。</h1>
          <p className="muted">先定义一个主题，再上传或发现论文。只有你明确选入且处理就绪的论文，才会成为后续报告的证据。</p>
          <WorkspaceForm
            topic={newTopic}
            language={newLanguage}
            submitLabel="创建第一个工作区"
            onTopicChange={setNewTopic}
            onLanguageChange={setNewLanguage}
            onSubmit={handleCreate}
            busy={busyKey === "create-workspace"}
          />
          {error && <p className="error-message">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">PAPERRAG / RESEARCH WORKSPACE</p>
          <h1>研究纸张，证据先行。</h1>
        </div>
        <div className="workspace-switcher">
          <label htmlFor="workspace-select">当前工作区</label>
          <select
            id="workspace-select"
            data-testid="workspace-select"
            value={workspaceId}
            onChange={(event) => setWorkspaceId(event.target.value)}
          >
            {workspaces.map((item) => (
              <option value={item.id} key={item.id}>
                {item.topic}
              </option>
            ))}
          </select>
        </div>
      </header>

      <main className="workspace-layout">
        <aside className="panel paper-boundary">
          <PanelHeading eyebrow="01 / EVIDENCE BOUNDARY" title="论文集合" />
          <div className="boundary-summary">
            <strong>{readyCount}</strong>
            <span>篇证据就绪</span>
            <small>Selected Papers：{selectedPapers.length} · 候选：{candidatePapers.length}</small>
          </div>
          <section>
            <SectionLabel label="Selected Papers" detail="可被下游工作使用" />
            {selectedPapers.length ? selectedPapers.map((paper) => <PaperCard key={paper.id} paper={paper} selected onImport={paper.evidence_readiness === "unavailable" ? () => void handleImport(paper) : undefined} onRemove={() => void runAction(`remove-${paper.id}`, async () => { await removePaper(workspace!.id, paper.id); setNotice("论文已移出当前证据边界，历史记录仍保留。 "); })} onRetry={() => void handleRetry(paper)} onUpload={(file) => setCandidateFiles((current) => ({ ...current, [paper.id]: file }))} candidateFile={candidateFiles[paper.id] ?? null} onCandidateUpload={(event) => void handleUpload(event, paper.id)} busyKey={busyKey} />) : <EmptyState text="还没有 Selected Paper。" />}
          </section>
          {unselectedPapers.length > 0 && (
            <section>
              <SectionLabel label="未选入的上传论文" detail="不会影响报告" />
              {unselectedPapers.map((paper) => (
                <PaperCard key={paper.id} paper={paper} onSelect={() => void runAction(`select-${paper.id}`, async () => { await selectPaper(workspace!.id, paper.id); setNotice("论文已加入 Selected Papers。 "); })} busyKey={busyKey} />
              ))}
            </section>
          )}
          <section>
            <SectionLabel label="Candidate Papers" detail="发现结果，尚未纳入证据" />
            {candidatePapers.length ? candidatePapers.map((paper) => <PaperCard key={paper.id} paper={paper} candidate onImport={() => void handleImport(paper)} onSelect={() => void runAction(`select-${paper.id}`, async () => { await selectPaper(workspace!.id, paper.id); setNotice("候选论文已选入，但仍需处理就绪后才能成为证据。 "); })} onUpload={(file) => setCandidateFiles((current) => ({ ...current, [paper.id]: file }))} candidateFile={candidateFiles[paper.id] ?? null} onCandidateUpload={(event) => void handleUpload(event, paper.id)} busyKey={busyKey} />) : <EmptyState text="运行一次主题发现，这里会出现候选论文。" />}
          </section>
        </aside>

        <section className="panel preparation-panel">
          <PanelHeading eyebrow="02 / PREPARE" title={workspace?.topic ?? "工作区准备"} />
          {workspace && (
            <>
              <div className="topic-block">
                <span className="status-dot" />
                <div>
                  <strong>{workspace.state === "active" ? "工作区已激活" : "工作区设置中"}</strong>
                  <p>报告语言：{workspace.report_language === "zh" ? "中文" : "English"}。先把 Selected Papers 准备好，下一步再生成并审批报告大纲。</p>
                </div>
              </div>

              <div className="card-block">
                <SectionLabel label="上传已授权的 Research Paper" detail="仅接受 PDF" />
                <form className="upload-row" onSubmit={(event) => void handleUpload(event)}>
                  <label className="file-picker">
                    <input data-testid="upload-paper" type="file" accept="application/pdf,.pdf" onChange={(event: ChangeEvent<HTMLInputElement>) => setUploadFile(event.target.files?.[0] ?? null)} />
                    <span>{uploadFile?.name ?? "选择 PDF 文件"}</span>
                  </label>
                  <button type="submit" disabled={!uploadFile || busyKey === "upload-paper"}>{busyKey === "upload-paper" ? "提交中…" : "上传并处理"}</button>
                </form>
                <p className="helper-text">直接上传的论文会进入 Selected Papers；解析或索引失败时可以在左侧按论文重试。</p>
              </div>

              <div className="card-block">
                <SectionLabel label="发现开放论文" detail="OpenAlex / arXiv" />
                <form className="discovery-form" onSubmit={(event) => void handleDiscover(event)}>
                  <input data-testid="discovery-query" value={discoveryQuery} onChange={(event) => setDiscoveryQuery(event.target.value)} placeholder="例如：RAG evidence attribution" />
                  <select value={provider} onChange={(event) => setProvider(event.target.value as "openalex" | "arxiv")} aria-label="发现来源">
                    <option value="openalex">OpenAlex</option>
                    <option value="arxiv">arXiv</option>
                  </select>
                  <button data-testid="discovery-submit" type="submit" disabled={!discoveryQuery.trim() || busyKey === "discover"}>{busyKey === "discover" ? "搜索中…" : "搜索候选"}</button>
                </form>
                {discovery && <DiscoverySummary discovery={discovery} />}
              </div>

              <div className="readiness-callout">
                <span className="callout-icon">↗</span>
                <div>
                  <strong>证据边界是显式的</strong>
                  <p>Candidate Papers 只提供元数据。只有 Selected Paper 且 Evidence Readiness 为“证据就绪”的论文，才会进入后续检索、生成和引用。</p>
                </div>
              </div>
            </>
          )}
          {notice && <p className="notice-message">{notice}</p>}
          {error && <p className="error-message">{error}</p>}
        </section>

        <aside className="panel activity-panel">
          <PanelHeading eyebrow="03 / DURABLE ACTIVITY" title="处理状态" />
          <p className="muted">这些状态来自持久化 Workspace Operations。刷新页面后仍会保留。</p>
          <section className="activity-list" aria-live="polite">
            {workspace?.operations.length ? workspace.operations.map((operation) => <OperationCard key={operation.id} operation={operation} papers={workspace.papers} onRetry={(paper) => void handleRetry(paper)} busyKey={busyKey} />) : <EmptyState text="上传或导入论文后，操作记录会出现在这里。" />}
          </section>
          <div className="new-workspace-block">
            <SectionLabel label="另建一个工作区" detail="单用户部署" />
            <WorkspaceForm
              compact
              topic={newTopic}
              language={newLanguage}
              submitLabel="创建"
              onTopicChange={setNewTopic}
              onLanguageChange={setNewLanguage}
              onSubmit={handleCreate}
              busy={busyKey === "create-workspace"}
            />
          </div>
        </aside>
      </main>
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
        <input data-testid="workspace-topic" value={topic} onChange={(event) => onTopicChange(event.target.value)} placeholder="新的研究主题" />
        <div className="inline-form">
          <select value={language} onChange={(event) => onLanguageChange(event.target.value as ReportLanguage)} aria-label="新工作区报告语言">
            <option value="zh">中文报告</option>
            <option value="en">English report</option>
          </select>
          <button data-testid="workspace-create" type="submit" disabled={!topic.trim() || busy}>{busy ? "创建中…" : submitLabel}</button>
        </div>
      </form>
    );
  }

  return (
    <form className="create-form" onSubmit={onSubmit}>
      <label>
        研究主题
        <input data-testid="workspace-topic" value={topic} onChange={(event) => onTopicChange(event.target.value)} placeholder="例如：RAG evidence attribution" autoFocus />
      </label>
      <label>
        Literature Report 语言
        <select value={language} onChange={(event) => onLanguageChange(event.target.value as ReportLanguage)}>
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
      </label>
      <button data-testid="workspace-create" type="submit" disabled={!topic.trim() || busy}>{busy ? "创建中…" : submitLabel}</button>
    </form>
  );
}

function PaperCard({
  paper,
  selected = false,
  candidate = false,
  onImport,
  onSelect,
  onRemove,
  onRetry,
  onUpload,
  candidateFile,
  onCandidateUpload,
  busyKey,
}: {
  paper: ResearchPaper;
  selected?: boolean;
  candidate?: boolean;
  onImport?: () => void;
  onSelect?: () => void;
  onRemove?: () => void;
  onRetry?: () => void;
  onUpload?: (file: File) => void;
  candidateFile?: File | null;
  onCandidateUpload?: (event: FormEvent<HTMLFormElement>) => void;
  busyKey: string | null;
}) {
  const importKey = `import-${paper.id}`;
  const selectKey = `select-${paper.id}`;
  const removeKey = `remove-${paper.id}`;
  const retryKey = `retry-${paper.id}`;
  const uploadKey = `upload-${paper.id}`;
  const needsAuthorisedFile = paper.evidence_readiness === "awaiting_authorised_file";
  return (
    <article className={`paper-card ${paper.evidence_eligible ? "paper-ready" : ""}`} data-testid={candidate ? "paper-candidate" : selected ? "paper-selected" : "paper-unselected"}>
      <div className="paper-card-heading">
        <div>
          <h3>{paper.title}</h3>
          <p>{paper.authors.slice(0, 3).join(" · ") || "作者信息未提供"}{paper.year && ` · ${paper.year}`}</p>
        </div>
        {paper.evidence_eligible ? <span className="badge badge-ready" data-testid="paper-evidence-eligible">Evidence eligible</span> : <span className={`badge badge-${paper.evidence_readiness}`}>{readinessLabels[paper.evidence_readiness]}</span>}
      </div>
      {paper.venue && <p className="paper-venue">{paper.venue}</p>}
      {paper.abstract && <p className="paper-abstract">{paper.abstract}</p>}
      {paper.source_url && <a className="paper-link" href={paper.source_url} target="_blank" rel="noreferrer">查看来源 ↗</a>}
      {paper.failure_message && <p className="paper-failure">{paper.failure_message}</p>}
      <div className="paper-actions">
        {(candidate || paper.evidence_readiness === "unavailable") && onImport && <button data-testid={`import-paper-${paper.id}`} type="button" onClick={onImport} disabled={busyKey === importKey}>{busyKey === importKey ? "提交中…" : paper.pdf_url && paper.is_open_access !== false ? "尝试导入 PDF" : "准备授权文件"}</button>}
        {candidate && onSelect && <button className="button-quiet" data-testid={`select-paper-${paper.id}`} type="button" onClick={onSelect} disabled={busyKey === selectKey}>先选入</button>}
        {!candidate && onSelect && <button type="button" onClick={onSelect} disabled={busyKey === selectKey}>{busyKey === selectKey ? "处理中…" : "加入 Selected Papers"}</button>}
        {selected && onRemove && <button className="button-quiet" data-testid={`remove-paper-${paper.id}`} type="button" onClick={onRemove} disabled={busyKey === removeKey}>移出证据边界</button>}
        {paper.retryable && onRetry && <button className="button-warning" data-testid={`retry-paper-${paper.id}`} type="button" onClick={onRetry} disabled={busyKey === retryKey}>{busyKey === retryKey ? "重试中…" : "重试处理"}</button>}
      </div>
      {needsAuthorisedFile && onCandidateUpload && (
        <form className="authorised-upload" onSubmit={onCandidateUpload}>
          <label className="file-picker compact">
            <input data-testid={`authorised-upload-${paper.id}`} type="file" accept="application/pdf,.pdf" onChange={(event: ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0]; if (file && onUpload) onUpload(file); }} />
            <span>{candidateFile?.name ?? "选择已授权 PDF"}</span>
          </label>
          <button type="submit" disabled={!candidateFile || busyKey === uploadKey}>{busyKey === uploadKey ? "提交中…" : "上传授权文件"}</button>
        </form>
      )}
    </article>
  );
}

function OperationCard({ operation, papers, onRetry, busyKey }: { operation: WorkspaceOperation; papers: ResearchPaper[]; onRetry: (paper: ResearchPaper) => void; busyKey: string | null }) {
  const paper = papers.find((item) => item.id === operation.paper_id);
  const percent = operation.total_work ? Math.round((operation.completed_work / operation.total_work) * 100) : 0;
  const active = operation.status === "queued" || operation.status === "running";
  return (
    <article className="operation-card" data-testid="operation-status">
      <div className="operation-heading">
        <strong>{operationLabels[operation.operation_type] || "工作区操作"}</strong>
        <span className={`operation-status status-${operation.status}`}>{operationStatusLabel(operation.status)}</span>
      </div>
      <p className="operation-paper">{paper?.title || "论文"}</p>
      <div className="progress-track"><span style={{ width: `${active ? Math.max(percent, operation.phase === "importing" ? 10 : 35) : percent}%` }} /></div>
      <div className="operation-meta"><span>{operation.phase}</span><span>{operation.completed_work}/{operation.total_work}</span></div>
      {operation.error_message && <p className="operation-error">{operation.error_message}</p>}
      {(operation.retry_action || operation.status === "failed" || operation.status === "interrupted") && paper && <button className="button-warning full-width" type="button" onClick={() => onRetry(paper)} disabled={busyKey === `retry-${paper.id}`}>恢复此操作</button>}
    </article>
  );
}

function DiscoverySummary({ discovery }: { discovery: DiscoveryResponse }) {
  return (
    <div className={`discovery-result discovery-${discovery.status}`} data-testid="discovery-results">
      <strong>{discovery.status === "succeeded" ? `已保存 ${discovery.candidates.length} 个候选` : discovery.status === "empty" ? "没有候选结果" : "发现失败"}</strong>
      <span>{discovery.error_message || "候选论文已加入左侧 Candidate Papers，可逐篇审阅。"}</span>
    </div>
  );
}

function PanelHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return <div className="panel-heading"><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>;
}

function SectionLabel({ label, detail }: { label: string; detail: string }) {
  return <div className="section-label"><strong>{label}</strong><span>{detail}</span></div>;
}

function EmptyState({ text }: { text: string }) {
  return <p className="empty-state">{text}</p>;
}

function operationStatusLabel(status: WorkspaceOperation["status"]): string {
  return { queued: "排队中", running: "处理中", succeeded: "已完成", failed: "失败", interrupted: "已中断", cancelled: "已取消" }[status];
}

function errorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : "请求失败，请检查服务状态后重试。";
}

createRoot(document.getElementById("root")!).render(<App />);
