# Development

## Tests

Install the development dependencies and run the complete test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

The test configuration requires 100% statement and branch coverage for the
`pcradio_mcp` package.

## Read-only container smoke test

The smoke test connects to MCP but does not execute device write operations:

```bash
docker compose run --rm --no-deps \
  -v ./tests:/tests:ro \
  pcradio-mcp python /tests/read_mcp.py
```

Run contract tests after changing a tool name, description, argument, return
value, server instruction, or safety restriction. A schema change is part of
the public MCP interface even when the PCRadio HTTP endpoint stays unchanged.
