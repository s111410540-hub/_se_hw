"""HTTP/1.1 Protocol Engine for mycurl.
Handles RFC 9112 compliant request generation and response parsing.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import socket


class CaseInsensitiveDict(dict):
    """A dictionary with case-insensitive string keys, preserving original case for display."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._keys: Dict[str, str] = {}
        self.update(*args, **kwargs)

    def __setitem__(self, key: str, value: str):
        lower = key.lower()
        self._keys[lower] = key
        super().__setitem__(lower, value)

    def __getitem__(self, key: str) -> str:
        return super().__getitem__(key.lower())

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return super().__contains__(key.lower())
        return False

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return super().get(key.lower(), default)

    def items(self):
        for lower_key, value in super().items():
            yield (self._keys.get(lower_key, lower_key), value)


@dataclass
class HTTPRequest:
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def to_bytes(self, host_header: str) -> bytes:
        """Formats the HTTP request into standard wire-format bytes."""
        normalized_method = self.method.upper()
        # Ensure path begins with /
        req_path = self.path if self.path.startswith("/") else f"/{self.path}"

        lines: List[str] = [f"{normalized_method} {req_path} HTTP/1.1"]

        # Track existing headers in lower-case
        header_keys_lower = {k.lower() for k in self.headers.keys()}

        # Mandatory / Default Headers
        if "host" not in header_keys_lower:
            lines.append(f"Host: {host_header}")
        if "user-agent" not in header_keys_lower:
            lines.append("User-Agent: mycurl/1.0")
        if "accept" not in header_keys_lower:
            lines.append("Accept: */*")
        if "connection" not in header_keys_lower:
            lines.append("Connection: close")

        # Custom Headers
        for key, value in self.headers.items():
            lines.append(f"{key}: {value}")

        # Content-Length for body if not present
        if self.body and "content-length" not in header_keys_lower:
            lines.append(f"Content-Length: {len(self.body)}")

        request_text = "\r\n".join(lines) + "\r\n\r\n"
        return request_text.encode("utf-8") + self.body


@dataclass
class HTTPResponse:
    version: str
    status_code: int
    reason: str
    headers: CaseInsensitiveDict
    raw_headers: List[str]
    body: bytes

    @property
    def text(self) -> str:
        """Decodes body to string using utf-8 with replacement on errors."""
        try:
            return self.body.decode("utf-8")
        except UnicodeDecodeError:
            return self.body.decode("latin-1", errors="replace")

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308)

    @property
    def location(self) -> Optional[str]:
        return self.headers.get("location")


class SocketReader:
    """Helper to read delimited lines and exact byte counts from a socket."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = bytearray()

    def read_until(self, delimiter: bytes) -> bytes:
        """Reads from socket until delimiter is encountered, returning the bytes up to and including delimiter."""
        while delimiter not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                # Connection closed prematurely
                result = bytes(self.buffer)
                self.buffer.clear()
                return result
            self.buffer.extend(chunk)

        idx = self.buffer.index(delimiter) + len(delimiter)
        result = bytes(self.buffer[:idx])
        del self.buffer[:idx]
        return result

    def read_exact(self, num_bytes: int) -> bytes:
        """Reads exactly num_bytes from buffer and socket."""
        while len(self.buffer) < num_bytes:
            chunk = self.sock.recv(min(4096, num_bytes - len(self.buffer)))
            if not chunk:
                break
            self.buffer.extend(chunk)

        read_count = min(len(self.buffer), num_bytes)
        result = bytes(self.buffer[:read_count])
        del self.buffer[:read_count]
        return result

    def read_all(self) -> bytes:
        """Reads until socket connection is closed (EOF)."""
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            self.buffer.extend(chunk)
        result = bytes(self.buffer)
        self.buffer.clear()
        return result


def parse_response(sock: socket.socket) -> HTTPResponse:
    """Reads and parses an HTTP/1.1 response from a connected socket."""
    reader = SocketReader(sock)

    # 1. Read Status-Line
    status_line_bytes = reader.read_until(b"\r\n")
    if not status_line_bytes:
        raise ConnectionResetError("Remote server closed connection without sending response.")

    status_line = status_line_bytes.decode("latin-1").strip()
    status_parts = status_line.split(" ", 2)
    if len(status_parts) < 2:
        raise ValueError(f"Invalid HTTP response status line: '{status_line}'")

    version = status_parts[0]
    status_code = int(status_parts[1])
    reason = status_parts[2] if len(status_parts) > 2 else ""

    # 2. Read Headers
    headers = CaseInsensitiveDict()
    raw_headers: List[str] = [status_line]

    while True:
        line_bytes = reader.read_until(b"\r\n")
        line = line_bytes.decode("latin-1").strip()
        if not line:  # Empty line marks end of headers
            break
        raw_headers.append(line)
        if ":" in line:
            header_name, header_value = line.split(":", 1)
            headers[header_name.strip()] = header_value.strip()

    # 3. Read Body based on headers
    transfer_encoding = headers.get("transfer-encoding", "").lower()
    content_length_str = headers.get("content-length")

    body_bytes = bytearray()

    if "chunked" in transfer_encoding:
        # Chunked Transfer Encoding
        while True:
            chunk_header = reader.read_until(b"\r\n").decode("latin-1").strip()
            # Chunk header is hex number optionally followed by chunk extensions
            chunk_size_str = chunk_header.split(";")[0].strip()
            if not chunk_size_str:
                break
            try:
                chunk_size = int(chunk_size_str, 16)
            except ValueError:
                raise ValueError(f"Invalid chunk size received: {chunk_size_str}")

            if chunk_size == 0:
                # End of chunks, consume trailing CRLF
                reader.read_until(b"\r\n")
                break

            chunk_data = reader.read_exact(chunk_size)
            body_bytes.extend(chunk_data)
            # Consume trailing CRLF after chunk data
            reader.read_until(b"\r\n")

    elif content_length_str is not None:
        try:
            content_length = int(content_length_str)
            body_bytes = bytearray(reader.read_exact(content_length))
        except ValueError:
            raise ValueError(f"Invalid Content-Length value: {content_length_str}")

    else:
        # Neither Chunked nor Content-Length -> read until EOF
        body_bytes = bytearray(reader.read_all())

    return HTTPResponse(
        version=version,
        status_code=status_code,
        reason=reason,
        headers=headers,
        raw_headers=raw_headers,
        body=bytes(body_bytes),
    )
