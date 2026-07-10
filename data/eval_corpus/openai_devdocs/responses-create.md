# Responses Create

## Required Request Shape

- A create request includes a model.
- A create request includes input.

## Optional Workflow Controls

- A request can include instructions.
- A request can include tools.
- Tool-enabled responses may return tool calls before a final answer.

## Follow-Up Turns

- Application code should send tool results back for another model turn.
- Structured request definitions make machine-readable behavior easier to
  validate.
