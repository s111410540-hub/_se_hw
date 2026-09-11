"""Integration tests using a local HTTP mock server."""
import http.server
import os
import socketserver
import tempfile
import threading
import unittest

from mycurl.client import MyCurlClient


class MockHTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/hello":
            body = b"Hello from local mock server!"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/hello")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path == "/check-header":
            custom_val = self.headers.get("X-Custom-Header", "missing")
            body = f"CustomHeader:{custom_val}".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/echo":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            response_body = b"Echoed: " + post_body
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress logging to keep test output clean
        pass


class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), MockHTTPHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_request(self):
        client = MyCurlClient()
        res = client.request(f"{self.base_url}/hello")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "Hello from local mock server!")

    def test_post_request(self):
        client = MyCurlClient()
        payload = b"test payload 123"
        res = client.request(
            url=f"{self.base_url}/echo",
            method="POST",
            headers={"Content-Type": "text/plain"},
            data=payload,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.body, b"Echoed: test payload 123")

    def test_custom_header(self):
        client = MyCurlClient()
        res = client.request(
            url=f"{self.base_url}/check-header",
            headers={"X-Custom-Header": "AwesomeCurl"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "CustomHeader:AwesomeCurl")

    def test_follow_redirect(self):
        client = MyCurlClient(follow_redirects=True)
        res = client.request(f"{self.base_url}/redirect")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, "Hello from local mock server!")

    def test_output_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            client = MyCurlClient(output_file=tmp_path)
            ret = client.run_and_output(f"{self.base_url}/hello")
            self.assertEqual(ret, 0)

            with open(tmp_path, "rb") as f:
                content = f.read()
            self.assertEqual(content, b"Hello from local mock server!")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
