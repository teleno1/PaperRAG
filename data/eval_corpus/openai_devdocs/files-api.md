# Files API

## Purpose

The Files API uploads and manages files that other workflows can reference.

## Core Behavior

- Uploaded files receive file ids.
- File ids can later be attached to vector stores.
- The Files API is about file lifecycle and attachment-ready assets.

## Boundary

- The Files API does not describe retrieval ranking.
- The Files API does not answer questions over documents by itself.
