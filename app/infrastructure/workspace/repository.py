from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.domain.workspace import (
    DiscoveryCandidate,
    DocumentVersion,
    ResearchPaper,
    ResearchWorkspace,
    WorkspaceOperation,
    normalize_doi,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    report_language TEXT NOT NULL CHECK (report_language IN ('zh', 'en')),
    state TEXT NOT NULL CHECK (state IN ('setup', 'active', 'archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    title TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('upload', 'discovery')),
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    selected INTEGER NOT NULL CHECK (selected IN (0, 1)),
    evidence_readiness TEXT NOT NULL,
    active_document_version_id TEXT,
    authors_json TEXT NOT NULL,
    year TEXT NOT NULL,
    venue TEXT NOT NULL,
    failure_phase TEXT,
    failure_message TEXT,
    retryable INTEGER NOT NULL CHECK (retryable IN (0, 1)),
    provider TEXT,
    provider_id TEXT,
    doi TEXT,
    arxiv_id TEXT,
    abstract TEXT NOT NULL DEFAULT '',
    source_url TEXT,
    pdf_url TEXT,
    is_open_access INTEGER,
    license TEXT,
    source_links_json TEXT NOT NULL DEFAULT '[]',
    discovery_query TEXT,
    discovered_at TEXT,
    published_at TEXT,
    source_updated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_versions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    paper_id TEXT NOT NULL REFERENCES papers(id),
    source_path TEXT NOT NULL,
    status TEXT NOT NULL,
    parsed_artifact_path TEXT,
    failure_phase TEXT,
    failure_message TEXT,
    requested_source_url TEXT,
    final_source_url TEXT,
    content_sha256 TEXT,
    imported_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_operations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    paper_id TEXT REFERENCES papers(id),
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    phase TEXT NOT NULL,
    error_category TEXT,
    error_message TEXT,
    retry_action TEXT,
    completed_work INTEGER NOT NULL DEFAULT 0,
    total_work INTEGER NOT NULL DEFAULT 1,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_papers_workspace ON papers(workspace_id, created_at);
CREATE INDEX IF NOT EXISTS idx_operations_workspace ON workspace_operations(workspace_id, created_at);
"""


class WorkspaceRepository:
    """Small sqlite3 repository for workspace state and provenance records."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            self._migrate_paper_columns(connection)
            self._migrate_document_version_columns(connection)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _migrate_paper_columns(connection: sqlite3.Connection) -> None:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(papers)").fetchall()}
        additions = {
            "provider": "TEXT",
            "provider_id": "TEXT",
            "doi": "TEXT",
            "arxiv_id": "TEXT",
            "abstract": "TEXT NOT NULL DEFAULT ''",
            "source_url": "TEXT",
            "pdf_url": "TEXT",
            "is_open_access": "INTEGER",
            "license": "TEXT",
            "source_links_json": "TEXT NOT NULL DEFAULT '[]'",
            "discovery_query": "TEXT",
            "discovered_at": "TEXT",
            "published_at": "TEXT",
            "source_updated_at": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE papers ADD COLUMN {name} {definition}")

    @staticmethod
    def _migrate_document_version_columns(connection: sqlite3.Connection) -> None:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(document_versions)").fetchall()}
        additions = {
            "requested_source_url": "TEXT",
            "final_source_url": "TEXT",
            "content_sha256": "TEXT",
            "imported_at": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE document_versions ADD COLUMN {name} {definition}")

    @staticmethod
    def _paper(row: sqlite3.Row) -> ResearchPaper:
        return ResearchPaper(
            id=row["id"],
            workspace_id=row["workspace_id"],
            title=row["title"],
            source_kind=row["source_kind"],
            original_filename=row["original_filename"],
            selected=bool(row["selected"]),
            evidence_readiness=row["evidence_readiness"],
            active_document_version_id=row["active_document_version_id"],
            authors=json.loads(row["authors_json"]),
            year=row["year"],
            venue=row["venue"],
            failure_phase=row["failure_phase"],
            failure_message=row["failure_message"],
            retryable=bool(row["retryable"]),
            provider=row["provider"],
            provider_id=row["provider_id"],
            doi=row["doi"],
            arxiv_id=row["arxiv_id"],
            abstract=row["abstract"],
            source_url=row["source_url"],
            pdf_url=row["pdf_url"],
            is_open_access=None if row["is_open_access"] is None else bool(row["is_open_access"]),
            license=row["license"],
            source_links=json.loads(row["source_links_json"] or "[]"),
            discovery_query=row["discovery_query"],
            discovered_at=row["discovered_at"],
            published_at=row["published_at"],
            source_updated_at=row["source_updated_at"],
        )

    def _workspace_with_connection(self, connection: sqlite3.Connection, workspace_id: str) -> ResearchWorkspace | None:
        workspace_row = connection.execute(
            "SELECT * FROM workspaces WHERE id = ?", (workspace_id,)
        ).fetchone()
        if workspace_row is None:
            return None
        paper_rows = connection.execute(
            "SELECT * FROM papers WHERE workspace_id = ? ORDER BY created_at, id", (workspace_id,)
        ).fetchall()
        return ResearchWorkspace(
            id=workspace_row["id"],
            topic=workspace_row["topic"],
            report_language=workspace_row["report_language"],
            state=workspace_row["state"],
            created_at=workspace_row["created_at"],
            updated_at=workspace_row["updated_at"],
            papers=[self._paper(row) for row in paper_rows],
        )

    def create_workspace(
        self,
        *,
        workspace_id: str,
        topic: str,
        report_language: str,
        timestamp: str,
    ) -> ResearchWorkspace:
        workspace = ResearchWorkspace(
            id=workspace_id,
            topic=topic,
            report_language=report_language,
            created_at=timestamp,
            updated_at=timestamp,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workspaces (id, topic, report_language, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace.id,
                    workspace.topic,
                    workspace.report_language,
                    workspace.state,
                    workspace.created_at,
                    workspace.updated_at,
                ),
            )
        return workspace

    def list_workspaces(self) -> list[ResearchWorkspace]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id FROM workspaces ORDER BY created_at, id").fetchall()
            return [self._workspace_with_connection(connection, row["id"]) for row in rows]

    def get_workspace(self, workspace_id: str) -> ResearchWorkspace | None:
        with self._connect() as connection:
            return self._workspace_with_connection(connection, workspace_id)

    def upsert_discovered_paper(
        self,
        *,
        paper_id: str,
        workspace_id: str,
        candidate: DiscoveryCandidate,
        original_filename: str,
        discovery_query: str,
        timestamp: str,
    ) -> ResearchPaper:
        normalized_doi = normalize_doi(candidate.doi)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM papers WHERE workspace_id = ? AND source_kind = 'discovery' ORDER BY created_at, id",
                (workspace_id,),
            ).fetchall()
            existing = next(
                (
                    row
                    for row in rows
                    if (normalized_doi and normalize_doi(row["doi"]) == normalized_doi)
                    or (
                        candidate.arxiv_id
                        and row["arxiv_id"]
                        and row["arxiv_id"].strip().lower() == candidate.arxiv_id.strip().lower()
                    )
                    or (
                        candidate.provider
                        and candidate.provider_id
                        and row["provider"] == candidate.provider
                        and row["provider_id"] == candidate.provider_id
                    )
                ),
                None,
            )
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO papers (
                        id, workspace_id, title, source_kind, original_filename, storage_path,
                        selected, evidence_readiness, active_document_version_id, authors_json,
                        year, venue, failure_phase, failure_message, retryable,
                        provider, provider_id, doi, arxiv_id, abstract, source_url, pdf_url,
                        is_open_access, license, source_links_json, discovery_query, discovered_at,
                        published_at, source_updated_at, created_at, updated_at
                    ) VALUES (?, ?, ?, 'discovery', ?, '', 0, 'unavailable', NULL, ?, ?, ?, NULL, NULL, 0,
                              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        workspace_id,
                        candidate.title,
                        original_filename,
                        json.dumps(candidate.authors, ensure_ascii=False),
                        candidate.year,
                        candidate.venue,
                        candidate.provider,
                        candidate.provider_id,
                        normalized_doi,
                        candidate.arxiv_id,
                        candidate.abstract,
                        candidate.source_url,
                        candidate.pdf_url,
                        None if candidate.is_open_access is None else int(candidate.is_open_access),
                        candidate.license,
                        json.dumps(candidate.source_links, ensure_ascii=False),
                        discovery_query,
                        candidate.published_at,
                        candidate.source_updated_at,
                        timestamp,
                        timestamp,
                        timestamp,
                    ),
                )
                row_id = paper_id
            else:
                previous_links = json.loads(existing["source_links_json"] or "[]")
                merged_links = list(previous_links)
                for link in candidate.source_links:
                    if link not in merged_links:
                        merged_links.append(link)
                connection.execute(
                    """
                    UPDATE papers
                    SET title = ?, authors_json = ?, year = ?, venue = ?,
                        provider = COALESCE(provider, ?), provider_id = COALESCE(provider_id, ?),
                        doi = COALESCE(doi, ?), arxiv_id = COALESCE(arxiv_id, ?),
                        abstract = CASE WHEN ? <> '' THEN ? ELSE abstract END,
                        source_url = COALESCE(source_url, ?), pdf_url = COALESCE(pdf_url, ?),
                        is_open_access = COALESCE(is_open_access, ?), license = COALESCE(license, ?),
                        source_links_json = ?, discovery_query = ?, discovered_at = ?,
                        published_at = COALESCE(?, published_at), source_updated_at = COALESCE(?, source_updated_at),
                        updated_at = ?
                    WHERE id = ? AND workspace_id = ?
                    """,
                    (
                        candidate.title,
                        json.dumps(candidate.authors, ensure_ascii=False),
                        candidate.year,
                        candidate.venue,
                        candidate.provider,
                        candidate.provider_id,
                        normalized_doi,
                        candidate.arxiv_id,
                        candidate.abstract,
                        candidate.abstract,
                        candidate.source_url,
                        candidate.pdf_url,
                        None if candidate.is_open_access is None else int(candidate.is_open_access),
                        candidate.license,
                        json.dumps(merged_links, ensure_ascii=False),
                        discovery_query,
                        timestamp,
                        candidate.published_at,
                        candidate.source_updated_at,
                        timestamp,
                        existing["id"],
                        workspace_id,
                    ),
                )
                row_id = existing["id"]
            connection.execute("UPDATE workspaces SET updated_at = ? WHERE id = ?", (timestamp, workspace_id))
            row = connection.execute("SELECT * FROM papers WHERE id = ?", (row_id,)).fetchone()
            if row is None:
                raise RuntimeError("discovered paper state could not be persisted")
            return self._paper(row)

    def begin_discovered_import(
        self,
        *,
        workspace_id: str,
        paper_id: str,
        document_version_id: str,
        storage_path: str,
        requested_source_url: str | None,
        timestamp: str,
    ) -> ResearchPaper | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ? AND workspace_id = ? AND source_kind = 'discovery'",
                (paper_id, workspace_id),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                INSERT INTO document_versions (
                    id, workspace_id, paper_id, source_path, status, parsed_artifact_path,
                    failure_phase, failure_message, requested_source_url, created_at
                ) VALUES (?, ?, ?, ?, 'importing', NULL, NULL, NULL, ?, ?)
                """,
                (document_version_id, workspace_id, paper_id, storage_path, requested_source_url, timestamp),
            )
            connection.execute(
                """
                UPDATE papers
                SET storage_path = ?, selected = 1, evidence_readiness = 'importing',
                    failure_phase = NULL,
                    failure_message = NULL, retryable = 0, updated_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (storage_path, timestamp, paper_id, workspace_id),
            )
            connection.execute("UPDATE workspaces SET state = 'active', updated_at = ? WHERE id = ?", (timestamp, workspace_id))
            updated = connection.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
            return self._paper(updated) if updated else None

    def mark_paper_awaiting_authorised_file(
        self,
        *,
        workspace_id: str,
        paper_id: str,
        timestamp: str,
    ) -> ResearchPaper | None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE papers
                SET selected = 1, evidence_readiness = 'awaiting_authorised_file',
                    active_document_version_id = NULL, failure_phase = 'import',
                    failure_message = 'No publicly downloadable PDF is available; upload an authorised PDF to use this paper.',
                    retryable = 0, updated_at = ?
                WHERE id = ? AND workspace_id = ? AND source_kind = 'discovery'
                """,
                (timestamp, paper_id, workspace_id),
            )
            connection.execute("UPDATE workspaces SET state = 'active', updated_at = ? WHERE id = ?", (timestamp, workspace_id))
            row = connection.execute("SELECT * FROM papers WHERE id = ? AND workspace_id = ?", (paper_id, workspace_id)).fetchone()
            return self._paper(row) if row else None

    def begin_authorised_upload(
        self,
        *,
        workspace_id: str,
        paper_id: str,
        document_version_id: str,
        original_filename: str,
        storage_path: str,
        timestamp: str,
    ) -> ResearchPaper | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM papers WHERE id = ? AND workspace_id = ? AND source_kind = 'discovery'",
                (paper_id, workspace_id),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                INSERT INTO document_versions (
                    id, workspace_id, paper_id, source_path, status, parsed_artifact_path,
                    failure_phase, failure_message, requested_source_url, created_at
                ) VALUES (?, ?, ?, ?, 'importing', NULL, NULL, NULL, NULL, ?)
                """,
                (document_version_id, workspace_id, paper_id, storage_path, timestamp),
            )
            connection.execute(
                """
                UPDATE papers
                SET original_filename = ?, storage_path = ?, selected = 1,
                    evidence_readiness = 'importing',
                    failure_phase = NULL, failure_message = NULL, retryable = 0, updated_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (original_filename, storage_path, timestamp, paper_id, workspace_id),
            )
            connection.execute("UPDATE workspaces SET state = 'active', updated_at = ? WHERE id = ?", (timestamp, workspace_id))
            updated = connection.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
            return self._paper(updated) if updated else None

    def create_uploaded_paper(
        self,
        *,
        paper_id: str,
        document_version_id: str,
        workspace_id: str,
        title: str,
        original_filename: str,
        storage_path: str,
        timestamp: str,
    ) -> ResearchPaper:
        paper = ResearchPaper(
            id=paper_id,
            workspace_id=workspace_id,
            title=title,
            source_kind="upload",
            original_filename=original_filename,
            selected=True,
            evidence_readiness="importing",
        )
        version = DocumentVersion(
            id=document_version_id,
            workspace_id=workspace_id,
            paper_id=paper_id,
            source_path=storage_path,
            status="importing",
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO papers (
                    id, workspace_id, title, source_kind, original_filename, storage_path,
                    selected, evidence_readiness, active_document_version_id, authors_json,
                    year, venue, failure_phase, failure_message, retryable, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper.id,
                    paper.workspace_id,
                    paper.title,
                    paper.source_kind,
                    paper.original_filename,
                    storage_path,
                    1,
                    paper.evidence_readiness,
                    None,
                    json.dumps(paper.authors),
                    paper.year,
                    paper.venue,
                    None,
                    None,
                    0,
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO document_versions (
                    id, workspace_id, paper_id, source_path, status, parsed_artifact_path,
                    failure_phase, failure_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version.id, version.workspace_id, version.paper_id, version.source_path, version.status, None, None, None, timestamp),
            )
            connection.execute(
                "UPDATE workspaces SET state = 'active', updated_at = ? WHERE id = ?",
                (timestamp, workspace_id),
            )
        return paper

    def mark_paper_ready(
        self,
        *,
        workspace_id: str,
        paper_id: str,
        document_version_id: str,
        parsed_artifact_path: str,
        timestamp: str,
        final_source_url: str | None = None,
        content_sha256: str | None = None,
        imported_at: str | None = None,
    ) -> ResearchPaper:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE papers
                SET evidence_readiness = 'ready', active_document_version_id = ?,
                    failure_phase = NULL, failure_message = NULL, retryable = 0, updated_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (document_version_id, timestamp, paper_id, workspace_id),
            )
            connection.execute(
                """
                UPDATE document_versions
                SET status = 'ready', parsed_artifact_path = ?, failure_phase = NULL, failure_message = NULL,
                    final_source_url = ?, content_sha256 = ?, imported_at = ?
                WHERE id = ? AND workspace_id = ? AND paper_id = ?
                """,
                (
                    parsed_artifact_path,
                    final_source_url,
                    content_sha256,
                    imported_at,
                    document_version_id,
                    workspace_id,
                    paper_id,
                ),
            )
            connection.execute("UPDATE workspaces SET updated_at = ? WHERE id = ?", (timestamp, workspace_id))
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ? AND workspace_id = ?", (paper_id, workspace_id)
            ).fetchone()
            if row is None:
                return None
            return self._paper(row)

    def mark_paper_failed(
        self,
        *,
        workspace_id: str,
        paper_id: str,
        document_version_id: str,
        failure_phase: str,
        failure_message: str,
        timestamp: str,
    ) -> ResearchPaper | None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE papers
                SET evidence_readiness = 'failed', failure_phase = ?, failure_message = ?,
                    retryable = 1, updated_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (failure_phase, failure_message, timestamp, paper_id, workspace_id),
            )
            connection.execute(
                """
                UPDATE document_versions
                SET status = 'failed', failure_phase = ?, failure_message = ?
                WHERE id = ? AND workspace_id = ? AND paper_id = ?
                """,
                (failure_phase, failure_message, document_version_id, workspace_id, paper_id),
            )
            connection.execute("UPDATE workspaces SET updated_at = ? WHERE id = ?", (timestamp, workspace_id))
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ? AND workspace_id = ?", (paper_id, workspace_id)
            ).fetchone()
            return self._paper(row) if row else None

    def set_paper_selected(self, *, workspace_id: str, paper_id: str, selected: bool, timestamp: str) -> ResearchPaper | None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE papers SET selected = ?, updated_at = ? WHERE id = ? AND workspace_id = ?",
                (int(selected), timestamp, paper_id, workspace_id),
            )
            connection.execute("UPDATE workspaces SET updated_at = ? WHERE id = ?", (timestamp, workspace_id))
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ? AND workspace_id = ?", (paper_id, workspace_id)
            ).fetchone()
            return self._paper(row) if row else None

    def interrupt_unfinished_operations(self, *, timestamp: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE workspace_operations
                SET status = 'interrupted', phase = 'interrupted',
                    error_category = 'operation_interrupted',
                    error_message = 'The service stopped before this operation finished.',
                    retry_action = 'retry', finished_at = ?, updated_at = ?
                WHERE status IN ('queued', 'running')
                """,
                (timestamp, timestamp),
            )
            connection.execute(
                """
                UPDATE papers
                SET evidence_readiness = 'failed', failure_phase = 'interrupted',
                    failure_message = 'The service stopped before paper processing finished.',
                    retryable = 1, updated_at = ?
                WHERE id IN (
                    SELECT paper_id FROM workspace_operations
                    WHERE status = 'interrupted' AND paper_id IS NOT NULL
                )
                AND evidence_readiness IN ('importing', 'parsing', 'indexing')
                """,
                (timestamp,),
            )

    def get_paper_storage_path(self, *, workspace_id: str, paper_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT storage_path FROM papers WHERE id = ? AND workspace_id = ?",
                (paper_id, workspace_id),
            ).fetchone()
            return row["storage_path"] if row else None

    def begin_paper_retry(
        self,
        *,
        workspace_id: str,
        paper_id: str,
        document_version_id: str,
        storage_path: str,
        timestamp: str,
    ) -> ResearchPaper | None:
        with self._connect() as connection:
            paper_row = connection.execute(
                "SELECT pdf_url FROM papers WHERE id = ? AND workspace_id = ?",
                (paper_id, workspace_id),
            ).fetchone()
            if paper_row is None:
                return None
            connection.execute(
                """
                INSERT INTO document_versions (
                    id, workspace_id, paper_id, source_path, status, parsed_artifact_path,
                    failure_phase, failure_message, requested_source_url, created_at
                ) VALUES (?, ?, ?, ?, 'importing', NULL, NULL, NULL, ?, ?)
                """,
                (
                    document_version_id,
                    workspace_id,
                    paper_id,
                    storage_path,
                    paper_row["pdf_url"],
                    timestamp,
                ),
            )
            connection.execute(
                """
                UPDATE papers
                SET storage_path = ?, evidence_readiness = 'importing',
                    failure_phase = NULL, failure_message = NULL, retryable = 0, updated_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (storage_path, timestamp, paper_id, workspace_id),
            )
            connection.execute("UPDATE workspaces SET state = 'active', updated_at = ? WHERE id = ?", (timestamp, workspace_id))
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ? AND workspace_id = ?", (paper_id, workspace_id)
            ).fetchone()
            return self._paper(row) if row else None

    def create_operation(
        self,
        *,
        operation_id: str,
        workspace_id: str,
        paper_id: str,
        operation_type: str,
        phase: str,
        timestamp: str,
    ) -> WorkspaceOperation:
        operation = WorkspaceOperation(
            id=operation_id,
            workspace_id=workspace_id,
            paper_id=paper_id,
            operation_type=operation_type,
            status="queued",
            phase=phase,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workspace_operations (
                    id, workspace_id, paper_id, operation_type, status, phase,
                    error_category, error_message, retry_action, completed_work, total_work,
                    started_at, finished_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    operation.id,
                    workspace_id,
                    paper_id,
                    operation.operation_type,
                    operation.status,
                    phase,
                    None,
                    None,
                    None,
                    0,
                    1,
                    None,
                    None,
                    timestamp,
                    timestamp,
                ),
            )
        return operation

    def update_operation(
        self,
        *,
        operation_id: str,
        status: str,
        phase: str,
        timestamp: str,
        error_category: str | None = None,
        error_message: str | None = None,
        retry_action: str | None = None,
        completed_work: int = 0,
        total_work: int = 1,
    ) -> WorkspaceOperation | None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE workspace_operations
                SET status = ?, phase = ?, error_category = ?, error_message = ?, retry_action = ?,
                    completed_work = ?, total_work = ?,
                    started_at = CASE WHEN ? = 'running' AND started_at IS NULL THEN ? ELSE started_at END,
                    finished_at = CASE WHEN ? IN ('succeeded', 'failed', 'cancelled', 'interrupted') THEN ? ELSE finished_at END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    phase,
                    error_category,
                    error_message,
                    retry_action,
                    completed_work,
                    total_work,
                    status,
                    timestamp,
                    status,
                    timestamp,
                    timestamp,
                    operation_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM workspace_operations WHERE id = ?", (operation_id,)
            ).fetchone()
            return self._operation(row) if row else None

    def get_operation(self, operation_id: str) -> WorkspaceOperation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workspace_operations WHERE id = ?", (operation_id,)
            ).fetchone()
            return self._operation(row) if row else None

    @staticmethod
    def _operation(row: sqlite3.Row) -> WorkspaceOperation:
        return WorkspaceOperation(
            id=row["id"],
            workspace_id=row["workspace_id"],
            paper_id=row["paper_id"],
            operation_type=row["operation_type"],
            status=row["status"],
            phase=row["phase"],
            error_category=row["error_category"],
            error_message=row["error_message"],
            retry_action=row["retry_action"],
            completed_work=row["completed_work"],
            total_work=row["total_work"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )
