# Structured Outputs

## Purpose

Structured outputs constrain model output to a declared JSON schema. This makes
machine-readable responses easier to validate and consume.

## What The Guarantee Covers

- Structured outputs focus on schema shape.
- A strict schema helps the model return the required fields.
- Structured outputs can be paired with tool definitions or other structured
  response patterns.

## Relation To JSON Mode

- Structured outputs are stronger than plain JSON mode.
- JSON mode aims for valid JSON text.
- Structured outputs aim for valid JSON that follows the declared schema.

## Boundaries

- Structured outputs do not guarantee factual correctness by themselves.
- Structured outputs help shape the response, not the grounding quality.
