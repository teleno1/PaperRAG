# Vector Store File Batches

## Purpose

File batches add multiple files to a vector store in one operation.

## Core Behavior

- A batch groups many file attachments together.
- Batch status and file counts help monitor ingestion progress.
- Batches are useful when many files must be indexed together.

## Boundary

- File batches are a store-population step.
- File batches are not a question-answering endpoint.
