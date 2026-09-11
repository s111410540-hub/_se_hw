"""Transport layer for mycurl.
Handles DNS resolution, TCP socket connection, and TLS/SSL encapsulation.
"""

from typing import Callable, Optional
import socket
import ssl


VerboseLogger = Callable[[str], None]


def create_connection(
    host: str,
    port: int,
    use_tls: bool = False,
    timeout: float = 10.0,
    log: Optional[VerboseLogger] = None,
) -> socket.socket:
    """Establishes a TCP socket connection, wraps in TLS if requested, and returns the socket."""
    if log is None:
        log = lambda msg: None

    log(f"* Resolving host: {host}...")
    try:
        # Resolve address (supports both IPv4 and IPv6)
        addr_info_list = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ConnectionError(f"Could not resolve host: {host} ({e})") from e

    last_error = None
    sock = None

    for family, socktype, proto, canonname, sockaddr in addr_info_list:
        ip = sockaddr[0]
        log(f"* Connecting to {ip} port {port}...")
        try:
            s = socket.socket(family, socktype, proto)
            s.settimeout(timeout)
            s.connect(sockaddr)
            sock = s
            log(f"* Connected to {host} ({ip}) port {port}")
            break
        except OSError as err:
            last_error = err
            if s:
                s.close()
            continue

    if sock is None:
        raise ConnectionError(f"Failed to connect to {host}:{port}: {last_error}")

    # If HTTPS, perform TLS handshake
    if use_tls:
        log("* Initializing SSL/TLS handshake...")
        context = ssl.create_default_context()
        try:
            tls_sock = context.wrap_socket(sock, server_hostname=host)
            log(f"* SSL connection established using {tls_sock.version()} / {tls_sock.cipher()[0]}")
            return tls_sock
        except Exception as e:
            sock.close()
            raise ConnectionError(f"SSL handshake failed with {host}: {e}") from e

    return sock
