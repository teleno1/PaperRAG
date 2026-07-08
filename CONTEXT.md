# PaperRAG

PaperRAG is a general, trustworthy knowledge-base RAG system evolved from an
academic paper-review prototype. This context defines the core product language
for retrieval, grounded generation, and evaluation.

## Product Language

**Corpus**:
The bounded collection of source documents that the system is allowed to ingest,
index, and retrieve from for a given workflow or evaluation run.
_Avoid_: Dataset, knowledge base dump

**Document**:
A source file or frozen source snapshot that is treated as one ingestible unit
before chunking.
_Avoid_: Paper, article

**Chunk**:
A contiguous unit of document content produced by parsing and chunking, used as
the primary retrieval payload.
_Avoid_: Passage, snippet

**Source**:
A traceable retrieval reference exposed to users and evaluators, usually tied to
one chunk and identified by `source_id`.
_Avoid_: Citation entry, reference row

**Answer Expectation**:
The offline evaluation label that states whether a case should be fully
answered, partially answered, or refused based on available corpus evidence.
_Avoid_: Mode, answer type

**Full Answer**:
An evaluation case where the corpus contains enough evidence to support the
requested answer directly.
_Avoid_: Normal case, positive case

**Partial Answer**:
An evaluation case where the corpus supports only part of the requested answer,
and the unsupported remainder must be explicitly left unresolved.
_Avoid_: Soft negative, incomplete positive

**Abstain**:
An evaluation case where the corpus does not support the requested answer, so a
grounded refusal or explicit statement of missing evidence is the correct behavior.
_Avoid_: No answer, hard negative

**Expected Source**:
A `source_id`-level gold evidence reference used only for offline evaluation to
judge retrieval and grounding quality.
_Avoid_: Gold chunk, runtime hint

**Unsupported Aspect**:
A requested detail that the corpus does not support and that the system must not
hallucinate as grounded.
_Avoid_: Missing field, negative note
