"""Launcher that serves the dashboard on a dual-stack socket.

Binding a plain `--host 127.0.0.1` (IPv4) or `--host ::` (IPv6-only on macOS) means
`http://localhost:PORT` breaks in browsers that resolve `localhost` to the other family.
This creates one IPv6 socket with IPV6_V6ONLY disabled so it accepts BOTH IPv4 (127.0.0.1)
and IPv6 (::1) — so `localhost` always works, whichever way it resolves.

Run: python backend/serve.py   (honours $PORT, default 8000)
"""
from __future__ import annotations

import os
import socket

import uvicorn


def make_dual_stack_socket(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # accept IPv4 too
    except (AttributeError, OSError):
        pass  # platform without the option; IPv6-only is the fallback
    sock.bind(("::", port))
    sock.listen(128)
    sock.set_inheritable(True)
    return sock


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    try:
        sock = make_dual_stack_socket(port)
    except OSError:
        # dual-stack unavailable (e.g. IPv6 disabled) → fall back to IPv4 loopback
        config = uvicorn.Config("app:app", host="127.0.0.1", port=port, log_level="info")
        uvicorn.Server(config).run()
        return
    config = uvicorn.Config("app:app", log_level="info")
    server = uvicorn.Server(config)
    server.run(sockets=[sock])


if __name__ == "__main__":
    main()
