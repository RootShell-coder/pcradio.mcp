# pcradio-mcp

An MCP server for reading and controlling a PCRadio internet radio through its
HTTP API. It uses the MCP Streamable HTTP transport.

This server is built specifically for the
[pcradio.esp32](https://github.com/RootShell-coder/pcradio.esp32) project.

## Features

- Read device state, playback details, network information, alarms, and
  playlists.
- Control playback, channels, volume, and mute state.
- Configure equalizer presets and audio effects.
- Manage user stations and alarms.
- Configure NTP servers, timezone, and Web UI preferences.
- Optionally protect the MCP endpoint with a static Bearer token.
- Return structured device error details, including HTTP status, error code,
  message, and additional context.

Deleting user stations, OTA, shutdown/standby, and the IR service are
intentionally not exposed as MCP tools.

## Run with Docker Compose

```bash
git clone https://github.com/RootShell-coder/pcradio.mcp.git
cd pcradio.mcp
export PCRADIO_BASE_URL=http://pcradio.local
docker compose pull
docker compose up -d
```

The MCP endpoint is available at:

```text
http://localhost:8081/mcp
```

## Configuration

| Variable           | Description                              | Default                        |
| ------------------ | ---------------------------------------- | ------------------------------ |
| `PCRADIO_BASE_URL` | PCRadio device HTTP API URL              | `http://pcradio.local`         |
| `PCRADIO_TIMEOUT`  | Device request timeout in seconds        | `5`                            |
| `MCP_HOST`         | Address listened on inside the container | `0.0.0.0`                      |
| `MCP_PORT`         | Port listened on inside the container    | `8080`                         |
| `MCP_BEARER_TOKEN` | Optional Bearer token required by `/mcp` | Empty; authentication disabled |

Values can be supplied as environment variables or through a `.env` file.

### Bearer authentication

When `MCP_BEARER_TOKEN` contains a non-empty value, clients must include it in
every MCP HTTP request:

```text
Authorization: Bearer <token>
```

Remove the variable or set it to an empty value to disable authentication. In
an MCP client configuration, `MCP_BEARER_TOKEN` can be used as the environment
variable containing the Bearer token.

## Tests

Install the development dependencies and run the complete test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

The test configuration requires 100% statement and branch coverage for the
`pcradio_mcp` package.

The read-only container smoke test does not execute device write operations:

```bash
docker compose run --rm --no-deps \
  -v ./tests:/tests:ro \
  pcradio-mcp python /tests/read_mcp.py
```
