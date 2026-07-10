from app.domain.eval.generation_metrics import (
    aggregate_generation_metrics,
    answer_point_coverage,
    abstention_cue_present,
    build_generation_case_metrics,
    citation_hit_rate,
    format_compliance,
    no_source_assertion_rate,
    unsupported_aspect_violation_count,
    unknown_citation_count,
)


def test_citation_hit_rate_counts_supported_citations() -> None:
    rate = citation_hit_rate(
        cited_source_ids=["s1", "s2", "s9"],
        expected_source_ids=["s1"],
        retrieved_source_ids=["s2", "s3"],
    )

    assert rate == 2 / 3


def test_unknown_citation_count_counts_ids_not_in_retrieved_sources() -> None:
    assert unknown_citation_count(["s1", "s9", "s9"], ["s1", "s2"]) == 1


def test_citation_hit_rate_can_credit_expected_but_unretrieved_ids() -> None:
    assert citation_hit_rate(["s1"], ["s1"], []) == 1.0
    assert unknown_citation_count(["s1"], []) == 1


def test_format_compliance_validates_json_markdown_and_bullet_summary() -> None:
    assert format_compliance('{"title":"Report","sections":[]}', "json") == 1.0
    assert format_compliance('{"title":"Report"}', "json") == 0.0
    assert format_compliance('{"title":"Report","sections":[1]}', "json") == 0.0
    assert format_compliance("# Report\n\n## Coverage\nSupports TXT ingestion. [Sources: s1]", "markdown") == 1.0
    assert format_compliance("# Report\n\nNo citations here.", "markdown") == 0.0
    assert format_compliance("# Report\n\n- Coverage: Supports TXT ingestion. [Sources: s1]", "bullet_summary") == 1.0
    assert format_compliance("# Report\n\n- Coverage: Supports TXT ingestion.\nStill covered. [Sources: s1]", "bullet_summary") == 1.0
    assert format_compliance("# Report\n\n- Coverage: Supports TXT ingestion.", "bullet_summary") == 0.0


def test_no_source_assertion_rate_is_deterministic_without_llm_judging() -> None:
    markdown_content = (
        "# Report\n\n"
        "## Coverage\n"
        "The system supports TXT ingestion. [Sources: s1]\n\n"
        "## Trust\n"
        "The system validates citations against retrieved chunks."
    )
    json_content = (
        '{"title":"Report","sections":['
        '{"title":"Coverage","body":"The system supports TXT ingestion.","cited_source_ids":["s1"]},'
        '{"title":"Trust","body":"The system validates citations against retrieved chunks.","cited_source_ids":[]}'
        "]}"
    )

    assert no_source_assertion_rate(markdown_content, "markdown") == 0.5
    assert no_source_assertion_rate(json_content, "json") == 0.5
    assert no_source_assertion_rate("[]", "json") == 1.0
    assert no_source_assertion_rate('{"title":"Report","sections":[1]}', "json") == 1.0


def test_answer_point_coverage_and_unsupported_aspects_are_deterministic() -> None:
    content = (
        "# Report\n\n"
        "## Coverage\n"
        "The system supports TXT ingestion and chunk identifiers. [Sources: s1]\n\n"
        "## Limits\n"
        "Pricing is not documented in the provided sources. [Sources: s1]"
    )

    assert answer_point_coverage(content, "markdown", ["TXT ingestion", "chunk identifiers", "source validation"]) == (2 / 3)
    assert unsupported_aspect_violation_count(content, "markdown", ["pricing", "model release date"]) == 0
    assert abstention_cue_present(content, "markdown") is True


def test_unsupported_aspect_violation_ignores_negated_boundary_mentions() -> None:
    content = (
        "# Report\n\n"
        "- Limits: The provided sources do not document account-level storage quotas for uploaded files. "
        "[Sources: s1]"
    )

    assert unsupported_aspect_violation_count(content, "bullet_summary", ["account-level storage quota"]) == 0


def test_aggregate_generation_metrics_is_deterministic() -> None:
    cases = [
        build_generation_case_metrics(
            cited_source_ids=["s1"],
            expected_source_ids=["s1"],
            retrieved_source_ids=["s1", "s2"],
            output_content="# Report\n\n## Coverage\nThe system supports TXT ingestion. [Sources: s1]",
            output_format="markdown",
            answer_points=["TXT ingestion"],
            unsupported_aspects=[],
        ),
        build_generation_case_metrics(
            cited_source_ids=["s9"],
            expected_source_ids=["s1"],
            retrieved_source_ids=["s1", "s2"],
            output_content="# Report\n\n- Coverage: The system supports TXT ingestion.",
            output_format="bullet_summary",
            answer_points=["TXT ingestion"],
            unsupported_aspects=["pricing"],
        ),
    ]

    metrics = aggregate_generation_metrics(cases)

    assert metrics.case_count == 2
    assert metrics.citation_hit_rate == 0.5
    assert metrics.unknown_citation_count == 1
    assert metrics.format_compliance_rate == 0.5
    assert metrics.no_source_assertion_rate == 0.5
    assert metrics.answer_point_coverage == 1.0
    assert metrics.unsupported_aspect_violation_count == 0
    assert metrics.abstention_cue_rate == 0.0
