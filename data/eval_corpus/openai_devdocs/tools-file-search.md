# File Search

## Purpose

The file search tool retrieves relevant chunks from prepared files so a model
can answer questions against a grounded document set.

## Setup Flow

- Upload files first.
- Add uploaded files to a vector store.
- Attach file search to the model workflow.
- Ask the question after the vector store is ready.

## Role In Grounded Answers

- File search retrieves relevant passages.
- File search works over prepared files, not over the public web.
- Applications still need to validate citations and present grounded answers.

## Boundaries

- File search is a retrieval tool.
- File search is not a pricing guide or product roadmap source.
