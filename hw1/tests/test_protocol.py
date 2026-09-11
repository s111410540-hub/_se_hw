"""Unit tests for Protocol Engine (Request & Response)."""
import unittest
from mycurl.protocol import (
    CaseInsensitiveDict,
    HTTPRequest,
    HTTPResponse,
    parse_response,
)


class DummySocket:
    """Mock socket that returns predefined bytes chunks from memory."""

    def __init__(self, data: bytes, chunk_size: int = 4096):
        self.data = data
        self.offset = 0
        self.chunk_size = chunk_size

    def recv(self, bufsize: int) -> bytes:
        if self.offset >= len(self.data):
            return b""
        size = min(bufsize, self.chunk_size, len(self.data) - self.offset)
        result = self.data[self.offset : self.offset + size]
        self.offset += size
        return result


class TestProtocolEngine(unittest.TestCase):
    def test_case_insensitive_dict(self):
        d = CaseInsensitiveDict()
        d["Content-Type"] = "text/html"
        d["X-CUSTOM-HEADER"] = "123"

        self.assertIn("content-type", d)
        self.assertIn("CONTENT-TYPE", d)
        self.assertEqual(d["content-type"], "text/html")
        self.assertEqual(d.get("x-custom-header"), "123")

    def test_request_to_bytes_default_headers(self):
        req = HTTPRequest(method="GET", path="/index.html")
        wire = req.to_bytes("example.com")

        self.assertIn(b"GET /index.html HTTP/1.1\r\n", wire)
        self.assertIn(b"Host: example.com\r\n", wire)
        self.assertIn(b"User-Agent: mycurl/1.0\r\n", wire)
        self.assertIn(b"Accept: */*\r\n", wire)
        self.assertIn(b"Connection: close\r\n", wire)
        self.assertTrue(wire.endswith(b"\r\n\r\n"))

    def test_request_with_body_and_content_length(self):
        req = HTTPRequest(
            method="POST",
            path="/api/login",
            headers={"Content-Type": "application/json"},
            body=b'{"user": "admin"}',
        )
        wire = req.to_bytes("api.example.com")

        self.assertIn(b"POST /api/login HTTP/1.1\r\n", wire)
        self.assertIn(b"Content-Type: application/json\r\n", wire)
        self.assertIn(b"Content-Length: 17\r\n", wire)
        self.assertTrue(wire.endswith(b'{"user": "admin"}'))

    def test_parse_response_with_content_length(self):
        raw = (
            b"HTTP/1.1 200 OK\r\n"
            b"Server: TestServer/1.0\r\n"
            b"Content-Type: text/plain\r\n"
            b"Content-Length: 12\r\n"
            b"\r\n"
            b"Hello World!"
        )
        mock_sock = DummySocket(raw)
        res = parse_response(mock_sock)

        self.assertEqual(res.version, "HTTP/1.1")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.reason, "OK")
        self.assertEqual(res.headers.get("content-type"), "text/plain")
        self.assertEqual(res.text, "Hello World!")
        self.assertFalse(res.is_redirect)

    def test_parse_response_chunked_transfer(self):
        # 5 bytes ("Wiki"), 6 bytes ("pedia "), 0 bytes (end)
        raw = (
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Content-Type: text/plain\r\n"
            b"\r\n"
            b"4\r\n"
            b"Wiki\r\n"
            b"6\r\n"
            b"pedia \r\n"
            b"0\r\n"
            b"\r\n"
        )
        mock_sock = DummySocket(raw)
        res = parse_response(mock_sock)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "Wikipedia ")

    def test_parse_response_redirect_status(self):
        raw = (
            b"HTTP/1.1 302 Found\r\n"
            b"Location: https://example.com/new\r\n"
            b"Content-Length: 0\r\n"
            b"\r\n"
        )
        mock_sock = DummySocket(raw)
        res = parse_response(mock_sock)

        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.is_redirect)
        self.assertEqual(res.location, "https://example.com/new")


if __name__ == "__main__":
    unittest.main()
