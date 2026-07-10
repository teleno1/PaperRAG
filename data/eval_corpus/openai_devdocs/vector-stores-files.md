# Vector Store Files

## Purpose

Vector store files attach uploaded files to a specific vector store.

## Core Behavior

- Use file ids from the Files API.
- Attachment tracks parsing and indexing status for that file inside the store.
- This step is about association and readiness.

## Boundary

- Vector store files are not a retrieval query interface.
