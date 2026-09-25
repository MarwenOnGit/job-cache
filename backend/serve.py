"""Launcher that serves the dashboard on loopback only, over both IPv4 and IPv6.

Binding a single family breaks `http://localhost:PORT` in browsers that resolve
`localhost` to the other one. Binding `::` (all interfaces) would fix that, but it
exposes your CV, materials and the /api/proxy fetcher to everyone on the same
network. So this opens two loopback sockets instead: 127.0.0.1 and ::1. Nothing
outside this machine can reach the app.

Run: python backend/serve.py   (honours $PORT, default 8000)
"""
from __future__ import annotations

import os
import socket
from typing import List

import uvicorn


def _bind(family: int, host: str, port: int) -> socket.socket:
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            # ::1 only; the IPv4 side gets its own 127.0.0.1 socket.
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.bind((host, port))
        sock.listen(128)
        sock.set_inheritable(True)
        return sock
    except OSError:
        sock.close()
        raise


def make_loopback_sockets(port: int) -> List[socket.socket]:
    """127.0.0.1 is required; ::1 is added when the machine has IPv6."""
    socks = [_bind(socket.AF_INET, "127.0.0.1", port)]
    try:
        socks.append(_bind(socket.AF_INET6, "::1", port))
    except OSError:
        pass  # IPv6 disabled: IPv4 loopback alone still serves http://localhost
    return socks


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = uvicorn.Server(uvicorn.Config("app:app", log_level="info"))
    server.run(sockets=make_loopback_sockets(port))


if __name__ == "__main__":
    main()
