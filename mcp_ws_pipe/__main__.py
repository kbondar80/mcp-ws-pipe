import argparse
import subprocess
import sys
import threading
import json
import logging
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed, WebSocketException


def setup_logging(logfile):
    """Configure logging to a file if specified."""
    if logfile:
        handler = logging.FileHandler(logfile, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(handler)


def main():
    parser = argparse.ArgumentParser(
        description="Connect local stdio (or a child process's stdio) to a remote WebSocket server"
    )
    parser.add_argument("url", help="WebSocket server URL (e.g., ws://example.com)")
    parser.add_argument(
        "--headers",
        "-H",
        help='Additional HTTP headers as JSON string (e.g., \'{"Authorization": "Bearer token"}\')',
    )
    parser.add_argument(
        "--log-messages",
        "-L",
        action="store_true",
        help="Enable logging of full request/response messages (no value; use --log-file to choose the path).",
    )
    parser.add_argument(
        "--log-file",
        default="mcp-ws-pipe.log",
        metavar="PATH",
        help="Log file path used when --log-messages is set (default: mcp-ws-pipe.log).",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help=(
            "Optional program and arguments to launch as a child process. "
            "Its stdio is piped through the WebSocket instead of this process's stdio. "
            "Use '--' to separate child flags from mcp-ws-pipe flags, e.g. "
            "mcp-ws-pipe ws://host -- some-program --flag arg"
        ),
    )
    args = parser.parse_args()

    # Guard against an option silently swallowing the URL (e.g. `-H wss://...`).
    if not args.url.startswith(("ws://", "wss://")):
        parser.error(
            f"URL must start with ws:// or wss:// (got {args.url!r}). "
            "Check that no preceding option consumed it as a value."
        )

    # Set up logging if specified
    setup_logging(args.log_file if args.log_messages else None)

    # Parse headers if provided
    headers = {}
    if args.headers:
        try:
            headers = json.loads(args.headers)
            if not isinstance(headers, dict):
                logging.error("Headers must be a JSON object")
                sys.exit(1)
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing headers JSON: {e}")
            sys.exit(1)

    # Flag to signal shutdown
    shutdown_event = threading.Event()
    
    # If a child command was provided, spawn it and use its stdio.
    # Otherwise, use this process's own stdin/stdout.
    proc = None
    if args.command:
        try:
            proc = subprocess.Popen(
                args.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                bufsize=1,
                text=True,
                encoding="utf-8",
            )
        except (OSError, ValueError) as e:
            logging.error(f"Failed to start child process {args.command!r}: {e}")
            sys.exit(1)
        input_stream = proc.stdout
        output_stream = proc.stdin
    else:
        input_stream = sys.stdin
        output_stream = sys.stdout

    stdin_thread = None

    def pump_input(websocket):
        """Read lines from the input stream and forward them to the WebSocket."""
        try:
            while not shutdown_event.is_set():
                line = input_stream.readline()
                if not line:  # EOF (parent stdin closed or child stdout closed)
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    websocket.send(line)
                    logging.info("REQUEST  (%d bytes): %s", len(line), line)
                except WebSocketException as e:
                    logging.error(f"Error sending message: {e}")
                    shutdown_event.set()
                    break
        except Exception as e:
            logging.error(f"Error reading input: {e}")
        finally:
            shutdown_event.set()

    try:
        with connect(args.url, additional_headers=headers) as websocket:
            # Start thread to read input and send synchronously
            stdin_thread = threading.Thread(target=pump_input, args=(websocket,))
            stdin_thread.daemon = True
            stdin_thread.start()

            # Main thread receives messages and writes them to the output stream
            while not shutdown_event.is_set():
                # If a child process was launched and has exited, stop.
                if proc is not None and proc.poll() is not None:
                    logging.info(f"Child process exited with code {proc.returncode}")
                    shutdown_event.set()
                    break
                try:
                    message = websocket.recv(timeout=1.0)
                    output_stream.write(message + "\n")
                    output_stream.flush()
                    logging.info("RESPONSE (%d bytes): %s", len(message), message)
                except TimeoutError:
                    continue
                except ConnectionClosed:
                    logging.error("WebSocket connection closed")
                    shutdown_event.set()
                    break
                except WebSocketException as e:
                    logging.error(f"Error receiving message: {e}")
                    shutdown_event.set()
                    break

    except WebSocketException as e:
        logging.error(f"WebSocket connection error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        shutdown_event.set()
        if proc is not None:
            # Closing the child's stdin lets it shut down cleanly on EOF.
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if stdin_thread is not None:
            stdin_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()