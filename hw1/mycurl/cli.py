"""CLI Interface for mycurl.
Parses command-line arguments and invokes MyCurlClient.
"""

import argparse
import base64
import sys
from typing import Dict, List, Optional

from .client import MyCurlClient
from . import __version__


def parse_headers(raw_headers: Optional[List[str]]) -> Dict[str, str]:
    """Parses a list of 'Header-Name: Value' strings into a dictionary."""
    headers: Dict[str, str] = {}
    if not raw_headers:
        return headers

    for h in raw_headers:
        if ":" in h:
            name, value = h.split(":", 1)
            headers[name.strip()] = value.strip()
        else:
            headers[h.strip()] = ""
    return headers


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mycurl",
        description="mycurl - A lightweight, modular HTTP/1.1 client for Modern Software Engineering.",
    )
    parser.add_argument("url", help="Target URL (e.g. http://example.com or https://httpbin.org/get)")
    parser.add_argument(
        "-X", "--request",
        default="GET",
        help="Specify request command to use (default: GET)",
    )
    parser.add_argument(
        "-H", "--header",
        action="append",
        help="Pass custom header(s) to server (e.g. -H 'Accept: application/json')",
    )
    parser.add_argument(
        "-d", "--data",
        help="HTTP POST data (sets method to POST if -X not explicitly specified)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Make the operation more talkative (print connection and header details)",
    )
    parser.add_argument(
        "-i", "--include",
        action="store_true",
        help="Include protocol response headers in the output",
    )
    parser.add_argument(
        "-o", "--output",
        help="Write to file instead of stdout",
    )
    parser.add_argument(
        "-L", "--location",
        action="store_true",
        help="Follow HTTP redirects (301, 302, etc.)",
    )
    parser.add_argument(
        "-u", "--user",
        help="Server user and password for Basic Authentication (e.g. user:password)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Maximum time allowed for connection and transfer in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(args: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    parsed_args = parser.parse_args(args)

    # Determine method
    method = parsed_args.request
    if parsed_args.data is not None and parsed_args.request == "GET":
        # If -d is given and -X was not altered from default GET, default to POST
        method = "POST"

    # Prepare data payload
    data_bytes = parsed_args.data.encode("utf-8") if parsed_args.data else None

    # Prepare headers
    headers = parse_headers(parsed_args.header)

    # Default Content-Type if -d is provided and not specified
    if data_bytes and not any(k.lower() == "content-type" for k in headers.keys()):
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    # Basic Authentication support (-u user:password)
    if parsed_args.user:
        auth_bytes = parsed_args.user.encode("utf-8")
        encoded_auth = base64.b64encode(auth_bytes).decode("ascii")
        headers["Authorization"] = f"Basic {encoded_auth}"

    client = MyCurlClient(
        verbose=parsed_args.verbose,
        follow_redirects=parsed_args.location,
        timeout=parsed_args.timeout,
        include_headers=parsed_args.include,
        output_file=parsed_args.output,
    )

    try:
        return client.run_and_output(
            url=parsed_args.url,
            method=method,
            headers=headers,
            data=data_bytes,
        )
    except Exception as e:
        if parsed_args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            sys.stderr.write(f"mycurl: (error) {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
