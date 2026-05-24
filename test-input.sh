#!/bin/sh
# Run like this:
# ./test-input.sh | uvx mcp-ws-pipe wss://example.com/mcp

# This script sends a series of MCP messages to the WebSocket server.
# It first sends an initialize message, then waits for 2 seconds,
# then sends a tools/list message, and finally waits for 5 seconds.
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","clientInfo":{"name":"wscat-client","version":"1.0.0"},"capabilities":{}},"id":1}'
sleep 2
echo '{"jsonrpc":"2.0","method":"tools/list","id":2}'
sleep 5

