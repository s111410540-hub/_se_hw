"""URL Parser module for mycurl.
Handles URL parsing, scheme extraction, port resolution, and path normalization.
"""

from dataclasses import dataclass
import urllib.parse


@dataclass
class ParsedURL:
    raw_url: str
    scheme: str          # 'http' or 'https'
    host: str            # domain name or IP
    port: int            # 80, 443, or custom
    path: str            # request path including query, e.g. '/api/v1?foo=bar'

    @property
    def is_tls(self) -> bool:
        return self.scheme == "https"

    @property
    def host_header(self) -> str:
        """Returns the appropriate Host header string (omitting default ports)."""
        if (self.scheme == "http" and self.port == 80) or (self.scheme == "https" and self.port == 443):
            return self.host
        return f"{self.host}:{self.port}"


def parse_url(url: str) -> ParsedURL:
    """Parses a raw URL string into a structured ParsedURL object.
    
    If no scheme is provided, 'http://' is prepended by default.
    """
    clean_url = url.strip()
    if not clean_url:
        raise ValueError("URL cannot be empty")

    if "://" in clean_url:
        scheme_prefix = clean_url.split("://", 1)[0].lower()
        if scheme_prefix not in ("http", "https"):
            raise ValueError(f"Unsupported scheme: {scheme_prefix}. Only 'http' and 'https' are supported.")
    else:
        # Default scheme is http
        clean_url = f"http://{clean_url}"

    parsed = urllib.parse.urlsplit(clean_url)

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {scheme}. Only 'http' and 'https' are supported.")

    host = parsed.hostname
    if not host:
        raise ValueError(f"Invalid URL: missing host in '{url}'")

    # Determine port
    if parsed.port is not None:
        port = parsed.port
    else:
        port = 443 if scheme == "https" else 80

    # Determine path and query
    path = parsed.path if parsed.path else "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    return ParsedURL(
        raw_url=clean_url,
        scheme=scheme,
        host=host,
        port=port,
        path=path
    )


def resolve_redirect_url(base_url: str, location: str) -> str:
    """Resolves relative or absolute redirect URLs against the base URL."""
    return urllib.parse.urljoin(base_url, location)
