# Deployment

## Docker Compose

```bash
git clone https://github.com/RootShell-coder/pcradio.mcp.git
cd pcradio.mcp
export PCRADIO_BASE_URL=http://pcradio.local
docker compose pull
docker compose up -d
```

The MCP endpoint is available at `http://localhost:8081/mcp`.

## Configuration

| Variable           | Description                              | Default                        |
| ------------------ | ---------------------------------------- | ------------------------------ |
| `PCRADIO_BASE_URL` | PCRadio device HTTP API URL              | `http://pcradio.local`         |
| `PCRADIO_TIMEOUT`  | Device request timeout in seconds        | `5`                            |
| `MCP_HOST`         | Address listened on inside the container | `0.0.0.0`                      |
| `MCP_PORT`         | Port listened on inside the container    | `8080`                         |
| `MCP_BEARER_TOKEN` | Optional Bearer token required by `/mcp` | Empty; authentication disabled |

Values can be supplied as environment variables or through a `.env` file.

## Bearer authentication

When `MCP_BEARER_TOKEN` is non-empty, clients must include this header in every
MCP HTTP request:

```text
Authorization: Bearer <token>
```

Remove the variable or set it to an empty value to disable authentication.

## Recommendations

- Keep PCRadio and the MCP server on a trusted network. Do not expose the
  device HTTP API directly to the internet.
- Set `MCP_BEARER_TOKEN` whenever the MCP endpoint is reachable outside the
  local host or a private container network.
- Terminate TLS at a reverse proxy when traffic leaves the trusted network.
- Give the model read-only access during initial evaluation. Enable write
  tools only after validating tool selection and argument accuracy.
- Pin a tested container image digest in production instead of a mutable tag.
- Preserve MCP server instructions and tool results in the client. Removing or
  summarizing them can change model behavior.
