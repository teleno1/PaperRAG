# Function Calling

## Purpose

Function calling lets a model return structured tool call arguments instead of
only natural-language text. It is useful when an application wants the model to
decide which tool to use and what arguments to send.

## Tool Definitions

- A tool definition should include a tool name.
- A tool definition should include a description.
- A tool definition should include a JSON schema for the arguments.
- The schema is how the model learns the expected argument fields and shapes.

## Runtime Loop

- The model can return a tool call request.
- Client code executes the tool.
- Client code sends the tool result back to the model.
- The model can use the tool result in a later response step.

## Boundaries

- Function calling structures tool call arguments.
- Function calling does not execute the tool.
- Application code is responsible for tool execution, validation, and retries.
