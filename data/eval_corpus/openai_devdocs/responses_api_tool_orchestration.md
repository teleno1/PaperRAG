# Responses API Tool Orchestration

## Example Flow

The cookbook example shows a loop:

- send the user request
- inspect tool calls
- execute the requested tools in client code
- send tool outputs back
- repeat until the model returns the final answer

## What The Example Emphasizes

- The application stays in control of tool execution.
- Multi-step orchestration can require several rounds.
- Tool calls and tool outputs are part of one iterative workflow.
