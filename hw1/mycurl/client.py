"""Client Controller module for mycurl.
Coordinates URL parsing, transport connection, HTTP protocol execution, redirects, and outputs.
"""

from typing import Dict, List, Optional
import sys
import os

from .url_parser import parse_url, resolve_redirect_url, ParsedURL
from .protocol import HTTPRequest, HTTPResponse, parse_response
from .transport import create_connection


class MyCurlClient:
    def __init__(
        self,
        verbose: bool = False,
        follow_redirects: bool = False,
        max_redirects: int = 10,
        timeout: float = 10.0,
        include_headers: bool = False,
        output_file: Optional[str] = None,
    ):
        self.verbose = verbose
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self.timeout = timeout
        self.include_headers = include_headers
        self.output_file = output_file

    def _log_verbose(self, message: str):
        """Prints verbose logs to stderr with standard curl formatting."""
        if self.verbose:
            sys.stderr.write(f"{message}\n")
            sys.stderr.flush()

    def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
    ) -> HTTPResponse:
        """Executes the HTTP request, handles redirects if configured, and returns the response."""
        current_url = url
        current_method = method.upper()
        current_headers = dict(headers or {})
        current_data = data or b""

        redirect_count = 0

        while True:
            parsed_url = parse_url(current_url)
            self._log_verbose(f"* Requesting URL: {current_url}")

            req = HTTPRequest(
                method=current_method,
                path=parsed_url.path,
                headers=current_headers,
                body=current_data,
            )

            req_bytes = req.to_bytes(parsed_url.host_header)

            sock = create_connection(
                host=parsed_url.host,
                port=parsed_url.port,
                use_tls=parsed_url.is_tls,
                timeout=self.timeout,
                log=self._log_verbose,
            )

            try:
                # Log outgoing request headers
                if self.verbose:
                    header_text = req_bytes.split(b"\r\n\r\n", 1)[0].decode("latin-1")
                    for line in header_text.split("\r\n"):
                        self._log_verbose(f"> {line}")
                    self._log_verbose(">")

                # Send request
                sock.sendall(req_bytes)

                # Parse response
                response = parse_response(sock)

                # Log incoming response headers
                if self.verbose:
                    for line in response.raw_headers:
                        self._log_verbose(f"< {line}")
                    self._log_verbose("<")

            finally:
                sock.close()

            # Handle redirects
            if self.follow_redirects and response.is_redirect:
                location = response.location
                if not location:
                    self._log_verbose("* Redirect received without Location header.")
                    break

                redirect_count += 1
                if redirect_count > self.max_redirects:
                    raise RuntimeError(f"Maximum redirect limit reached ({self.max_redirects})")

                next_url = resolve_redirect_url(current_url, location)
                self._log_verbose(f"* Issue another request to this URL: '{next_url}'")

                # Standard HTTP redirect behavior: 303 or 301/302 change POST to GET
                if response.status_code == 303 or (response.status_code in (301, 302) and current_method == "POST"):
                    current_method = "GET"
                    current_data = b""
                    current_headers.pop("Content-Type", None)
                    current_headers.pop("content-type", None)

                current_url = next_url
                continue

            break

        return response

    def run_and_output(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
    ) -> int:
        """Executes request and outputs result to stdout or file based on flags."""
        response = self.request(url, method, headers, data)

        output_data = bytearray()

        if self.include_headers:
            header_str = "\r\n".join(response.raw_headers) + "\r\n\r\n"
            output_data.extend(header_str.encode("latin-1"))

        output_data.extend(response.body)

        if self.output_file:
            with open(self.output_file, "wb") as f:
                f.write(output_data)
            self._log_verbose(f"* Output saved to {self.output_file}")
        else:
            sys.stdout.buffer.write(output_data)
            sys.stdout.buffer.flush()

        # Returns 0 if response received
        return 0
