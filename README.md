# mcp-ws-pipe

A CLI tool to connect local stdio (standard input/output) to a remote WebSocket server.

## Overview

`mcp-ws-pipe` is designed to be complementary to [ws-mcp](https://github.com/nick1udwig/ws-mcp), which wraps stdio MCP servers with websockets. This tool provides the client-side functionality, allowing you to connect to those websocket servers from your terminal.

Unlike [wscat](https://github.com/websockets/wscat), `mcp-ws-pipe` doesn't output prompts like `>` and `<` which can confuse MCP clients.

## Installation

### Using pip

```bash
pip install mcp-ws-pipe
```

### Using UVX

```bash
uvx install mcp-ws-pipe
```

## Usage

### Standard Usage

```bash
mcp-ws-pipe wss://example.com/socket
```

With additional headers:

```bash
mcp-ws-pipe wss://example.com/socket --headers '{"Authorization": "Bearer token"}'
# or using the short form
mcp-ws-pipe wss://example.com/socket -H '{"Authorization": "Bearer token"}'
```

### Direct UVX Execution

Run the tool directly with UVX without installing it first:

```bash
uvx mcp-ws-pipe wss://example.com/socket
```

With additional headers:

```bash
uvx mcp-ws-pipe wss://example.com/socket --headers '{"Authorization": "Bearer token"}'
```

## Features

- Clean bidirectional communication between stdio and websockets
- No confusing prompts or formatting that could interfere with MCP clients
- Asynchronous handling of input/output
- Proper error handling and connection management

## Development

```bash
# Clone the repository
git clone <repository-url>
cd mcp-ws-pipe

# Install dependencies
uv pip install -e .

# Run the application
python -m mcp_ws_pipe <websocket-url>
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.