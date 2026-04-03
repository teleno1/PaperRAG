from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

CitationPolicy = Literal["required", "optional", "none"]
WriteStage = Literal["body", "final_pass"]


class OutlineNode(BaseModel):
    node_id: str = ""
    title: str
    description: str = ""
    query: str = ""
    needs_retrieval: bool = True
    write_stage: WriteStage = "body"
    citation_policy: CitationPolicy = "required"
    subsections: List["OutlineNode"] = Field(default_factory=list)


class LeafSection(BaseModel):
    chapter_id: str
    chapter_title: str
    section_id: str
    title: str
    description: str = ""
    query: str = ""
    citation_policy: CitationPolicy = "required"
    write_stage: WriteStage = "body"


class PlannedChapter(BaseModel):
    chapter_id: str
    chapter_title: str
    chapter_description: str = ""
    query: str = ""
    citation_policy: CitationPolicy = "required"
    write_stage: WriteStage = "body"
    leaf_sections: List[LeafSection] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    title: str = ""
    language: str = "中文"
    body_chapters: List[PlannedChapter] = Field(default_factory=list)
    final_pass_chapters: List[PlannedChapter] = Field(default_factory=list)


class RetrievedSource(BaseModel):
    source_id: str
    paper_id: str
    chunk_id: str
    title: str = ""
    authors: List[str] = Field(default_factory=list)
    year: str = ""
    venue: str = ""
    section: str = ""
    content: str
    paper_score: Optional[float] = None
    chunk_score: Optional[float] = None


class SectionSourceFile(BaseModel):
    chapter_id: str
    chapter_title: str
    section_id: str
    section_title: str
    section_description: str = ""
    section_query: str = ""
    citation_policy: CitationPolicy = "required"
    source_ids: List[str] = Field(default_factory=list)
    sources: List[RetrievedSource] = Field(default_factory=list)


class SectionBundle(BaseModel):
    section_id: str
    section_title: str
    section_description: str = ""
    section_query: str = ""
    citation_policy: CitationPolicy = "required"
    source_ids: List[str] = Field(default_factory=list)


class ChapterBundle(BaseModel):
    chapter_id: str
    chapter_title: str
    chapter_description: str = ""
    chapter_query: str = ""
    chapter_citation_policy: CitationPolicy = "required"
    leaf_sections: List[SectionBundle] = Field(default_factory=list)
    unique_sources: List[RetrievedSource] = Field(default_factory=list)
    all_source_ids: List[str] = Field(default_factory=list)


class SourceRegistry(BaseModel):
    source_id_to_chunk_id: Dict[str, str] = Field(default_factory=dict)
    source_id_to_paper_id: Dict[str, str] = Field(default_factory=dict)
    paper_id_to_metadata: Dict[str, Dict] = Field(default_factory=dict)


class SentenceDraft(BaseModel):
    sentence_id: str
    text: str
    cite_source_ids: List[str] = Field(default_factory=list)


class ParagraphDraft(BaseModel):
    paragraph_id: str
    sentences: List[SentenceDraft] = Field(default_factory=list)


class SectionDraft(BaseModel):
    section_id: str
    section_title: str
    paragraphs: List[ParagraphDraft] = Field(default_factory=list)


class ChapterDraft(BaseModel):
    chapter_id: str
    chapter_title: str
    paragraphs: List[ParagraphDraft] = Field(default_factory=list)
    sections: List[SectionDraft] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class ReferenceEntry(BaseModel):
    ref_no: int
    paper_id: str
    title: str = ""
    authors: List[str] = Field(default_factory=list)
    year: str = ""
    venue: str = ""


class CitationRegistry(BaseModel):
    paper_id_to_ref_no: Dict[str, int] = Field(default_factory=dict)
    source_id_to_paper_id: Dict[str, str] = Field(default_factory=dict)
    paper_id_to_metadata: Dict[str, Dict] = Field(default_factory=dict)
    references: List[ReferenceEntry] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    level: Literal["error", "warning"]
    code: str
    message: str
    location: str = ""


class ValidationReport(BaseModel):
    ok: bool = True
    issues: List[ValidationIssue] = Field(default_factory=list)
    stats: Dict[str, Dict] = Field(default_factory=dict)


OutlineNode.model_rebuild()
