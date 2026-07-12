# Single-process local workspace topology

PaperRAG's first version is a React + TypeScript single-page workspace served
by the same FastAPI application that exposes its `/api` contracts. SQLite plus
managed local files are the durable store, and a single-Uvicorn-worker,
in-process executor runs persisted Workspace Operations. This deliberately
favours a reliable, private, self-hosted single-user package over Docker,
database services, queues, authentication, or horizontal scaling; those would
need a new task-execution and access-control design before adoption.
