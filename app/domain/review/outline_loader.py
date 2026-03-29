from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from app.domain.review.models import ExecutionPlan, LeafSection, OutlineNode, PlannedChapter

ABSTRACT_TITLES = {"摘要", "abstract"}
CHAPTER_ID_TEMPLATE = "CH{index:02d}"
FINAL_PASS_ID_TEMPLATE = "FP{index:02d}"
SECTION_ID_TEMPLATE = "{chapter_id}-SEC{index:02d}"


def _read_json_file(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_outline(outline_path: str | Path) -> Dict:
    path = Path(outline_path)
    data = _read_json_file(path)
    if not isinstance(data, dict):
        raise ValueError("Outline file must be a JSON object.")
    if "sections" not in data or not isinstance(data["sections"], list):
        raise ValueError("Outline file must contain a sections list.")
    return data


def _normalize_node(raw: Dict) -> OutlineNode:
    return OutlineNode(
        title=raw.get("title", ""),
        description=raw.get("description", ""),
        query=raw.get("query", ""),
        needs_retrieval=bool(raw.get("needs_retrieval", True)),
        write_stage=raw.get("write_stage", "body"),
        citation_policy=raw.get("citation_policy", "required"),
        subsections=[_normalize_node(item) for item in raw.get("subsections", [])],
    )


def normalize_outline(raw_outline: Dict) -> Dict:
    title = raw_outline.get("title", "")
    language = raw_outline.get("language", "中文")
    sections = [_normalize_node(section) for section in raw_outline.get("sections", [])]
    return {
        "title": title,
        "language": language,
        "sections": [section.model_dump() for section in sections],
    }


def _iter_leaf_nodes(
    node: OutlineNode,
    chapter_id: str,
    chapter_title: str,
    counter: List[int],
) -> List[LeafSection]:
    if not node.subsections:
        counter[0] += 1
        section_id = SECTION_ID_TEMPLATE.format(chapter_id=chapter_id, index=counter[0])
        return [
            LeafSection(
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                section_id=section_id,
                title=node.title,
                description=node.description,
                query=node.query,
                citation_policy=node.citation_policy,
                write_stage=node.write_stage,
            )
        ]

    leaves: List[LeafSection] = []
    for child in node.subsections:
        leaves.extend(_iter_leaf_nodes(child, chapter_id, chapter_title, counter))
    return leaves


def build_execution_plan(raw_outline: Dict) -> ExecutionPlan:
    title = raw_outline.get("title", "")
    language = raw_outline.get("language", "中文")
    normalized_sections = [_normalize_node(section) for section in raw_outline.get("sections", [])]

    body_chapters: List[PlannedChapter] = []
    final_pass_chapters: List[PlannedChapter] = []

    body_idx = 0
    final_idx = 0
    for section in normalized_sections:
        if section.write_stage == "body":
            body_idx += 1
            chapter_id = CHAPTER_ID_TEMPLATE.format(index=body_idx)
            leaf_counter = [0]
            leaves = _iter_leaf_nodes(section, chapter_id, section.title, leaf_counter)
            body_chapters.append(
                PlannedChapter(
                    chapter_id=chapter_id,
                    chapter_title=section.title,
                    chapter_description=section.description,
                    query=section.query,
                    citation_policy=section.citation_policy,
                    write_stage=section.write_stage,
                    leaf_sections=leaves,
                )
            )
        else:
            final_idx += 1
            chapter_id = FINAL_PASS_ID_TEMPLATE.format(index=final_idx)
            final_pass_chapters.append(
                PlannedChapter(
                    chapter_id=chapter_id,
                    chapter_title=section.title,
                    chapter_description=section.description,
                    query=section.query,
                    citation_policy=section.citation_policy,
                    write_stage=section.write_stage,
                    leaf_sections=[],
                )
            )

    finals_non_abstract = [chapter for chapter in final_pass_chapters if chapter.chapter_title.strip().lower() not in ABSTRACT_TITLES]
    finals_abstract = [chapter for chapter in final_pass_chapters if chapter.chapter_title.strip().lower() in ABSTRACT_TITLES]

    return ExecutionPlan(
        title=title,
        language=language,
        body_chapters=body_chapters,
        final_pass_chapters=finals_non_abstract + finals_abstract,
    )


def dump_json(obj, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = obj.model_dump() if hasattr(obj, "model_dump") else obj
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def make_outline_summary(plan: ExecutionPlan) -> str:
    lines = [
        f"Title: {plan.title}",
        f"Language: {plan.language}",
        "Body chapters:",
    ]
    for idx, chapter in enumerate(plan.body_chapters, start=1):
        lines.append(f"{idx}. {chapter.chapter_title}")
    if plan.final_pass_chapters:
        lines.append("Final-pass chapters:")
        for idx, chapter in enumerate(plan.final_pass_chapters, start=1):
            lines.append(f"{idx}. {chapter.chapter_title}")
    return "\n".join(lines)

