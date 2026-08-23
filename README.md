# pcradio-mcp

An MCP server for reading and controlling a PCRadio internet radio through its
HTTP API. It uses the MCP Streamable HTTP transport and is built for the
[pcradio.esp32](https://github.com/RootShell-coder/pcradio.esp32) project.

## Capabilities

- Read device state, playback details, network information, alarms, and
  playlists.
- Control playback, channels, volume, mute state, equalizer, and audio effects.
- Manage user stations, alarms, time settings, and Web UI preferences.
- Protect the MCP endpoint with optional Bearer authentication.
- Return structured device errors to MCP clients.

Deleting user stations, OTA, shutdown/standby, and the IR service are
intentionally not exposed as MCP tools.

## Documentation

- [Deployment and configuration](docs/DEPLOYMENT.md)
- [Language model requirements and recommendations](docs/MODEL_REQUIREMENTS.md)
- [Development and tests](docs/DEVELOPMENT.md)
- [LinkedIn article package](docs/linkedin/README.md)
