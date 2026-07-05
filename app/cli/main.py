"""PaperRAG command line interface."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import PaperRAGError
from app.core.logging import setup_logging
from app.use_cases.build_index import BuildIndexUseCase
from app.use_cases.generate_outline import GenerateOutlineUseCase
from app.use_cases.health_and_state import HealthAndStateUseCase
from app.use_cases.prepare_corpus import PrepareCorpusUseCase
from app.use_cases.run_eval import RunEvalUseCase
from app.use_cases.run_query import RunQueryUseCase
from app.use_cases.run_report import RunReportUseCase
from app.use_cases.run_review_from_outline import RunReviewFromOutlineUseCase
from app.use_cases.run_review_from_topic import RunReviewFromTopicUseCase


def _print_parser_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


def cmd_corpus_prepare(args) -> int:
    try:
        result = PrepareCorpusUseCase().execute(force=args.force)
        print(
            json.dumps(
                {
                    "papers_dir": str(result.papers_dir),
                    "processed_dir": str(result.processed_dir),
                    "total_papers": result.total_papers,
                    "successful": result.successful,
                    "failed": result.failed,
                    "results": result.results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if result.failed == 0 else 1
    except PaperRAGError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_index_build(args) -> int:
    try:
        start_time = time.time()
        result = BuildIndexUseCase().execute(force=args.force)
        print(
            json.dumps(
                {
                    "database_dir": str(result.database_dir),
                    "index_path": str(result.index_path),
                    "metadata_path": str(result.metadata_path),
                    "total_vectors": result.total_vectors,
                    "elapsed_time": time.time() - start_time,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except PaperRAGError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_outline_generate(args) -> int:
    try:
        outline_path = GenerateOutlineUseCase().execute(
            topic=args.topic,
            output_path=Path(args.output) if args.output else None,
        )
        print(json.dumps({"topic": args.topic, "outline_path": str(outline_path)}, ensure_ascii=False, indent=2))
        return 0
    except PaperRAGError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_review_run(args) -> int:
    try:
        result = RunReviewFromTopicUseCase().execute(topic=args.topic, ensure_index=not args.skip_index_check)
        print(
            json.dumps(
                {
                    "outline_path": str(result.outline_path),
                    "run_dir": str(result.run_dir),
                    "final_review_md": str(result.final_review_md),
                    "final_review_txt": str(result.final_review_txt),
                    "final_review_json": str(result.final_review_json),
                    "references_json": str(result.references_json),
                    "validation_report": str(result.validation_report),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except PaperRAGError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_review_run_from_outline(args) -> int:
    outline_path = Path(args.outline)
    if not outline_path.exists():
        print(f"Outline file does not exist: {outline_path}", file=sys.stderr)
        return 1
    try:
        result = RunReviewFromOutlineUseCase().execute(outline_path=outline_path)
        print(
            json.dumps(
                {
                    "outline_path": str(result.outline_path),
                    "run_dir": str(result.run_dir),
                    "final_review_md": str(result.final_review_md),
                    "final_review_txt": str(result.final_review_txt),
                    "final_review_json": str(result.final_review_json),
                    "references_json": str(result.references_json),
                    "validation_report": str(result.validation_report),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except PaperRAGError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_query_run(args) -> int:
    try:
        result = RunQueryUseCase().execute(
            query=args.query,
            top_k=args.top_k,
            include_retrieved_sources=not args.hide_sources,
        )
        print(result.model_dump_json(indent=2))
        return 0
    except PaperRAGError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_report_run(args) -> int:
    try:
        result = RunReportUseCase().execute(
            query=args.query,
            output_format=args.format,
            top_k=args.top_k,
        )
        print(result.model_dump_json(indent=2))
        return 0
    except PaperRAGError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_eval_run(args) -> int:
    try:
        start_time = time.time()
        result = RunEvalUseCase().execute(
            dataset=args.dataset,
            top_k=args.top_k,
        )
        payload = result.model_dump(mode="json")
        payload["elapsed_time"] = time.time() - start_time
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except PaperRAGError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_state(args) -> int:
    state = HealthAndStateUseCase().get_state()
    print(
        json.dumps(
            {
                "pdf_count": state.pdf_count,
                "processed_count": state.processed_count,
                "index_ready": state.index_ready,
                "vector_count": state.vector_count,
                "outlines_count": state.outlines_count,
                "latest_run_dir": state.latest_run_dir,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_health(args) -> int:
    health = HealthAndStateUseCase().get_health()
    print(
        json.dumps(
            {
                "ok": health.ok,
                "missing_keys": health.missing_keys,
                "state": {
                    "pdf_count": health.state.pdf_count if health.state else 0,
                    "processed_count": health.state.processed_count if health.state else 0,
                    "index_ready": health.state.index_ready if health.state else False,
                    "vector_count": health.state.vector_count if health.state else 0,
                    "outlines_count": health.state.outlines_count if health.state else 0,
                    "latest_run_dir": health.state.latest_run_dir if health.state else None,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if health.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=get_settings().project.name)
    subparsers = parser.add_subparsers(dest="command")

    corpus_parser = subparsers.add_parser("corpus", help="Corpus operations")
    corpus_subparsers = corpus_parser.add_subparsers(dest="corpus_command")
    corpus_prepare_parser = corpus_subparsers.add_parser("prepare", help="Prepare parsed corpus")
    corpus_prepare_parser.add_argument("--force", action="store_true", help="Force reparsing")
    corpus_prepare_parser.set_defaults(func=cmd_corpus_prepare)

    index_parser = subparsers.add_parser("index", help="Index operations")
    index_subparsers = index_parser.add_subparsers(dest="index_command")
    index_build_parser = index_subparsers.add_parser("build", help="Build vector index")
    index_build_parser.add_argument("--force", action="store_true", help="Force rebuild index")
    index_build_parser.set_defaults(func=cmd_index_build)

    outline_parser = subparsers.add_parser("outline", help="Outline operations")
    outline_subparsers = outline_parser.add_subparsers(dest="outline_command")
    outline_generate_parser = outline_subparsers.add_parser("generate", help="Generate outline")
    outline_generate_parser.add_argument("--topic", "-t", required=True, help="Review topic")
    outline_generate_parser.add_argument("--output", "-o", help="Custom outline path")
    outline_generate_parser.set_defaults(func=cmd_outline_generate)

    query_parser = subparsers.add_parser("query", help="General query operations")
    query_parser.set_defaults(func=lambda args, parser=query_parser: _print_parser_help(parser))
    query_subparsers = query_parser.add_subparsers(dest="query_command")
    query_run_parser = query_subparsers.add_parser("run", help="Run a cited answer query")
    query_run_parser.add_argument("--query", "-q", required=True, help="User query")
    query_run_parser.add_argument("--top-k", type=int, default=None, help="Optional retrieval depth override")
    query_run_parser.add_argument("--hide-sources", action="store_true", help="Return trace-only source metadata")
    query_run_parser.set_defaults(func=cmd_query_run)

    report_parser = subparsers.add_parser("report", help="General report operations")
    report_parser.set_defaults(func=lambda args, parser=report_parser: _print_parser_help(parser))
    report_subparsers = report_parser.add_subparsers(dest="report_command")
    report_run_parser = report_subparsers.add_parser("run", help="Run a cited report request")
    report_run_parser.add_argument("--query", "-q", required=True, help="Report request")
    report_run_parser.add_argument("--format", choices=["markdown", "json", "bullet_summary"], default="markdown", help="Output format")
    report_run_parser.add_argument("--top-k", type=int, default=None, help="Optional retrieval depth override")
    report_run_parser.set_defaults(func=cmd_report_run)

    eval_parser = subparsers.add_parser("eval", help="Evaluation operations")
    eval_parser.set_defaults(func=lambda args, parser=eval_parser: _print_parser_help(parser))
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command")
    eval_run_parser = eval_subparsers.add_parser("run", help="Run evaluation over a dataset")
    eval_run_parser.add_argument("--dataset", required=True, help="Path to eval dataset JSONL")
    eval_run_parser.add_argument("--top-k", type=int, default=None, help="Optional retrieval depth override")
    eval_run_parser.set_defaults(func=cmd_eval_run)

    review_parser = subparsers.add_parser("review", help="Review operations (legacy compatibility)")
    review_parser.set_defaults(func=lambda args, parser=review_parser: _print_parser_help(parser))
    review_subparsers = review_parser.add_subparsers(dest="review_command")
    review_run_parser = review_subparsers.add_parser("run", help="Run review from topic (legacy compatibility)")
    review_run_parser.add_argument("--topic", "-t", required=True, help="Review topic")
    review_run_parser.add_argument("--skip-index-check", action="store_true", help="Skip index preparation")
    review_run_parser.set_defaults(func=cmd_review_run)

    review_outline_parser = review_subparsers.add_parser("run-from-outline", help="Run review from outline (legacy compatibility)")
    review_outline_parser.add_argument("--outline", "-o", required=True, help="Outline JSON path")
    review_outline_parser.set_defaults(func=cmd_review_run_from_outline)

    state_parser = subparsers.add_parser("state", help="Show project state")
    state_parser.set_defaults(func=cmd_state)

    health_parser = subparsers.add_parser("health", help="Run health checks")
    health_parser.set_defaults(func=cmd_health)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    setup_logging()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
