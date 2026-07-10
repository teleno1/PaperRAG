# Responses API Overview

## Purpose

The Responses API is the modern API surface for model responses, tool use, and
structured generation workflows.

## Core Role

- A response can contain model-generated text.
- A response can contain tool calls.
- The same workflow can continue across follow-up turns.

## Why It Matters

- The Responses API brings generation and tool use into one main surface.
- It is the API family used by the final corpus for tool-enabled workflows.
