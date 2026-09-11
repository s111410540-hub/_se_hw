"""Unit tests for URL Parser module."""
import unittest
from mycurl.url_parser import parse_url, resolve_redirect_url, ParsedURL


class TestURLParser(unittest.TestCase):
    def test_basic_http_url(self):
        url = parse_url("http://example.com")
        self.assertEqual(url.scheme, "http")
        self.assertEqual(url.host, "example.com")
        self.assertEqual(url.port, 80)
        self.assertEqual(url.path, "/")
        self.assertFalse(url.is_tls)
        self.assertEqual(url.host_header, "example.com")

    def test_basic_https_url(self):
        url = parse_url("https://example.com/test")
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.host, "example.com")
        self.assertEqual(url.port, 443)
        self.assertEqual(url.path, "/test")
        self.assertTrue(url.is_tls)
        self.assertEqual(url.host_header, "example.com")

    def test_custom_port(self):
        url = parse_url("http://localhost:8080/api/users?page=1")
        self.assertEqual(url.scheme, "http")
        self.assertEqual(url.host, "localhost")
        self.assertEqual(url.port, 8080)
        self.assertEqual(url.path, "/api/users?page=1")
        self.assertEqual(url.host_header, "localhost:8080")

    def test_default_scheme_prepend(self):
        url = parse_url("example.com/foo")
        self.assertEqual(url.scheme, "http")
        self.assertEqual(url.host, "example.com")
        self.assertEqual(url.path, "/foo")

    def test_unsupported_scheme_raises(self):
        with self.assertRaises(ValueError):
            parse_url("ftp://example.com/file")

    def test_empty_url_raises(self):
        with self.assertRaises(ValueError):
            parse_url("")

    def test_resolve_redirect_relative(self):
        resolved = resolve_redirect_url("http://example.com/foo/bar", "/target")
        self.assertEqual(resolved, "http://example.com/target")

    def test_resolve_redirect_absolute(self):
        resolved = resolve_redirect_url("http://example.com/foo", "https://other.org/api")
        self.assertEqual(resolved, "https://other.org/api")


if __name__ == "__main__":
    unittest.main()
