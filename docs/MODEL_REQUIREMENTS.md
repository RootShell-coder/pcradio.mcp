# Language model requirements

The server publishes its operating rules through MCP server instructions and
JSON Schemas. A model does not need PCRadio-specific training, but the MCP
client must pass those instructions, tool schemas, tool results, and the
conversation history to the model without rewriting them.

The following values are practical deployment limits for this server, not MCP
protocol requirements:

| Requirement      | Minimum                                  | Recommended                          |
| ---------------- | ---------------------------------------- | ------------------------------------ |
| Local model size | 14B parameters                           | 20B or more                          |
| Input context    | 16k tokens                               | 32k tokens or more                   |
| Output allowance | 2k tokens                                | 4k tokens                            |
| Russian language | Reliable instruction following           | Native-quality understanding         |
| Tool use         | Native function calling with JSON Schema | Reliable multi-step function calling |

Models below 14B are not recommended for write access. They may select a
plausible but incorrect tool, confuse a station number with a user-station
number, or invent an alarm ID or revision. Parameter count is only a rough
filter: validate every candidate against the complete tool contract test set
before granting write access.

The model and client must support:

- JSON Schema descriptions, required and optional arguments, enums, numeric
  limits, and nullable values;
- sequential tool calls, including read-before-write and write-then-verify;
- returning tool results to the same conversation until the task is complete;
- exact use of device-provided IDs, channel numbers, and revision values;
- Russian requests without translating identifiers or enum values.

## Minimal model context

An MCP-aware client should use the server instructions automatically. If the
client ignores them, add this system prompt without duplicating tool details:

```text
You control PCRadio only through the connected PCRadio MCP server.
Follow the server instructions and tool schemas exactly.
Use the device values returned by tools; never invent IDs, channel numbers, or revisions.
Read current state before an update that requires existing values.
Verify a write when the user needs its resulting state.
If no exposed tool can perform an operation, say that the operation is unavailable.
Reply in the user's language.
```

Do not place the complete tool catalogue in the system prompt. The MCP client
already supplies it, and duplication wastes context and can create conflicting
contracts after a server update.

## Model choice

For a hosted deployment, **Gemini 3.7 Flash** is the preferred starting point:
it is intended for reliable multi-step agentic workflows, supports function
calling and structured output, and has more context than this server requires.
**Gemini 3.6 Flash** is a suitable lower-cost alternative when it passes the
same contract tests.

For local inference, **gpt-oss-20b** is the recommended minimum. It has 21B
total parameters, native function calling and structured output, a 128k-token
context window, and can run in approximately 16 GB of memory. Its training data
is mostly English, so Russian requests must be evaluated before production.

## Runtime recommendations

- Prefer deterministic or low-variance generation settings when the provider
  exposes them. Keep documented agentic defaults when sampling controls are
  unavailable or deprecated.
- Use automatic tool selection. Do not force a tool based only on keywords.
- Keep parallel tool calls disabled unless operations are independent and the
  client preserves result order. Device writes should be sequential.
- Do not retry writes automatically after a timeout. Read device state first,
  because the original request may already have succeeded.
- Keep the complete current tool schema in context. Remove unrelated history
  before removing MCP instructions or tool results.
- Require explicit confirmation before exposing any future destructive tool.
  OTA, IR, shutdown/standby, and deletion of user stations remain unavailable.

## Model evaluation

Evaluate a model with real Russian formulations before allowing write access.
At minimum, verify that it can:

1. distinguish a status question from a state-changing command;
2. distinguish catalogue channels from user playlist channels;
3. search before selecting a station when only a name is provided;
4. read current values before partial updates;
5. preserve alarm IDs and revision values returned by the device;
6. report an unavailable operation instead of substituting another tool;
7. recover from device errors without repeating a write blindly.

Record the selected tool, arguments, tool result, final response, latency, and
correctness. Compare models by successful task completion, not conversational
style. A model that fails an identifier, revision, or write-retry case should
remain read-only.

References: [Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/latest-model),
[Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling),
and [gpt-oss](https://openai.com/index/introducing-gpt-oss/).
