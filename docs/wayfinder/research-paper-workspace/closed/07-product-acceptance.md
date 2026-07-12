---
type: grilling
status: closed
claimed_by: Codex
blocked_by: []
resolved: 2026-07-12
---

# Define Product Acceptance and Demonstration Evidence

## Question

What end-to-end scenarios, compact demo corpus, observability, and objective
checks demonstrate that the product works as a research workspace—not merely
that it reports generic RAG metrics?

The decision must retain only measurements that support product trust, such as
traceability and citation-review behavior, and define a repeatable portfolio
demonstration without pretending a tiny corpus represents enterprise scale.

## Resolution

Product acceptance is a browser-visible workflow, not a generic RAG scorecard.
The required end-to-end scenarios are: (1) create a workspace, select papers,
process them, approve an outline, and generate a cited report; (2) inspect a
multi-source Claim and see every cited paper's title, page/section, and excerpt;
(3) edit a Claim and resolve its pending-review citation through confirmation or
successful refresh; and (4) show partial readiness or evidence removal, its
Evidence Coverage or evidence-unavailable state, and a Markdown export that
preserves the attention notice.

The Demonstration Corpus is exactly ten frozen open-access papers on RAG
evidence attribution and citation reliability. The report is Chinese even
though source papers are English. The manifest contains only source metadata
and provenance, never PDFs or derived artifacts, and must freeze the exact
arXiv version, final OA-PDF URL, SHA-256, licence/source record, and one of
these roles for every paper:

| Role | Frozen paper |
| --- | --- |
| Foundation / retrieval method | Patrick Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* — arXiv:2005.11401 |
| Foundation / retrieval method | Gautier Izacard and Edouard Grave, *Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering* — arXiv:2007.01282 |
| Foundation / retrieval method | Sebastian Borgeaud et al., *Improving Language Models by Retrieving from Trillions of Tokens* — arXiv:2112.04426 |
| Evidence attribution / citation mechanism | Jacob Menick et al., *Teaching Language Models to Support Answers with Verified Quotes* — arXiv:2203.11147 |
| Evidence attribution / citation mechanism | Bernd Bohnet et al., *Attributed Question Answering: Evaluation and Modeling for Attributed Large Language Models* — arXiv:2212.08037 |
| Evidence attribution / citation mechanism | Tianyu Gao et al., *Enabling Large Language Models to Generate Text with Citations* — arXiv:2305.14627 |
| Evaluation / factual consistency | Shahul Es et al., *RAGAS: Automated Evaluation of Retrieval Augmented Generation* — arXiv:2309.15217 |
| Evaluation / factual consistency | Dongyu Ru et al., *RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation* — arXiv:2408.08067 |
| Limitation / comparison / failure mode | Nelson F. Liu et al., *Lost in the Middle: How Language Models Use Long Contexts* — arXiv:2307.03172 |
| Limitation / comparison / failure mode | Mojtaba Komeili et al., *Internet-Augmented Dialogue Generation* — arXiv:2107.07566 |

An explicit demo-preparation and preflight command targets an empty, isolated
data directory and validates all ten entries. Any missing, non-PDF, changed, or
insufficiently documented source fails preflight; it never silently becomes a
smaller corpus. The partial-readiness/error scenario instead uses a controlled
local fixture, never a deliberately broken public URL. The test suite uses only
offline fakes for parsing, retrieval, discovery, and LLM generation; the real
OA run is manual portfolio acceptance after preflight.

The real demonstration report must have all ten papers selected and ready, at
least eight cited Claims spanning at least six papers, and at least two Claims
with two or more cited Source Chunks. It also shows one evidence-gap or
controlled-exception state. These are evidence-structure and workflow gates,
not claims of answer accuracy or enterprise RAG performance.

All automated acceptance scenarios must deterministically prove that every
visible citation resolves to at least one same-workspace, same-version
SourceAnchor; ineligible evidence cannot stay verified; substantive edits enter
pending review and only successful refresh restores verified; and workspace,
report, citation, and operation state survives browser reload and service
restart. Acceptance output is a local, machine-readable pass/fail summary plus
the product's local operation history and Report Trust Summary. No third-party
analytics, telemetry, generated reports, indexes, PDFs, or run logs are
committed. The portfolio package contains the manifest, an executable demo
script, automated tests, and an external 3–5 minute recorded real-OA demo.
