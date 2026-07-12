from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.domain.workspace import (
    DocumentVersion,
    ResearchPaper,
    ResearchWorkspace,
    WorkspaceOperation,
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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

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
                SET status = 'ready', parsed_artifact_path = ?, failure_phase = NULL, failure_message = NULL
                WHERE id = ? AND workspace_id = ? AND paper_id = ?
                """,
                (parsed_artifact_path, document_version_id, workspace_id, paper_id),
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
        timestamp: str,
    ) -> ResearchPaper | None:
        with self._connect() as connection:
            paper_row = connection.execute(
                "SELECT storage_path FROM papers WHERE id = ? AND workspace_id = ?",
                (paper_id, workspace_id),
            ).fetchone()
            if paper_row is None:
                return None
            connection.execute(
                """
                INSERT INTO document_versions (
                    id, workspace_id, paper_id, source_path, status, parsed_artifact_path,
                    failure_phase, failure_message, created_at
                ) VALUES (?, ?, ?, ?, 'importing', NULL, NULL, NULL, ?)
                """,
                (document_version_id, workspace_id, paper_id, paper_row["storage_path"], timestamp),
            )
            connection.execute(
                """
                UPDATE papers
                SET evidence_readiness = 'importing', active_document_version_id = NULL,
                    failure_phase = NULL, failure_message = NULL, retryable = 0, updated_at = ?
                WHERE id = ? AND workspace_id = ?
                """,
                (timestamp, paper_id, workspace_id),
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
