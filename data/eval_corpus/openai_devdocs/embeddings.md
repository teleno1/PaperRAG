# Embeddings

## Purpose

Embeddings convert text into vectors that can be compared in a shared numeric
space. Common uses include search, clustering, grouping similar passages, and
retrieval-augmented generation.

## Retrieval Workflow

- Chunk documents before embedding them.
- Store chunk metadata alongside each vector.
- Use the same embedding model for indexed chunks and query text.
- Compare query vectors to stored vectors during similarity search.

## Practical Notes

- Chunking affects retrieval quality.
- Embeddings support retrieval, but they do not generate the final answer.
- The retrieval system still needs source ids and chunk ids for traceability.
