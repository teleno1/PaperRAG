# Freeze the final eval corpus as a narrow OpenAI developer-doc snapshot

The final evaluation corpus is a frozen, in-repo snapshot of `12-18` OpenAI
developer-document sources limited to guides, API reference, and a small number
of cookbook examples around Responses, structured outputs, function calling,
embeddings, and vector-store or file-search-adjacent topics. We chose this over
broader web crawls, synthetic distractor documents, or ad hoc local PDFs because
the final eval asset needs to be reproducible, human-auditable, narrow enough to
annotate well, and still realistic enough to surface retrieval, citation, and
abstention failures.
