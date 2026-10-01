#!/usr/bin/env python3
"""Offline gate: the product never talks to the network and needs no online service.

Rules
-----
* ``network-import``  — no HTTP/socket client library is imported by product code. A local-only
                        ``socket.gethostname()`` is allowed (it reads the machine name); anything that
                        can open a connection is not.
* ``network-call``    — no ``urlopen``/``create_connection``/``socket.socket``/``http.client`` calls.
* ``network-dependency`` — ``pyproject.toml`` lists no network framework as a runtime dependency, so a
                        clinic installation can never depend on an online service.

The gate complements, but does not replace, the operational test: the packaged application is launched
with no network access in the release checklist.

Usage::

    python tools/qa/check_offline.py
    python tools/qa/check_offline.py --release
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib

from _common import REPO_ROOT, SRC_ROOT, Gate, parse_args, python_files, waived

#: Modules that imply network capability. ``socket`` is handled separately because reading the local
#: host name is not network access; ``asyncio``/``threading`` are not listed at all.
FORBIDDEN_MODULES = {
    "aiohttp",
    "anyio",
    "ftplib",
    "http.client",
    "httpx",
    "imaplib",
    "poplib",
    "requests",
    "smtplib",
    "telnetlib",
    "urllib.request",
    "urllib3",
    "webbrowser",
    "websocket",
    "websockets",
    "xmlrpc",
}

#: Socket operations that leave the machine (or listen for connections). Only these are forbidden when
#: ``socket`` is imported; ``gethostname``/``getfqdn``/``gethostbyaddr``-free usage stays acceptable.
SOCKET_EGRESS = re.compile(
    r"\b(connect|connect_ex|bind|listen|accept|send|sendall|sendto|recv|recvfrom|create_connection|"
    r"getaddrinfo|gethostbyname|gethostbyname_ex|create_server)\s*\("
)
NETWORK_CALL = re.compile(r"\b(urlopen|urlretrieve|Request\(|urljoin)\s*\(")

#: Runtime dependencies that would make the product depend on a service. Empty by design; the list
#: exists so a future accidental addition fails this gate instead of shipping.
FORBIDDEN_DEPENDENCIES = {
    "boto3",
    "firebase-admin",
    "google-cloud-storage",
    "httpx",
    "paho-mqtt",
    "pymongo",
    "redis",
    "requests",
    "supabase",
    "websocket-client",
}


def _imported_modules(tree: ast.AST) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append((node.module, node.lineno))
    return found


def check_imports(gate: Gate) -> None:
    for path in python_files():
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        gate.checked += 1
        try:
            tree = ast.parse(text)
        except SyntaxError:  # pragma: no cover - the test suite reports syntax errors first
            continue
        for module, lineno in _imported_modules(tree):
            root = module.split(".")[0]
            dotted = module if module.count(".") <= 1 else ".".join(module.split(".")[:2])
            forbidden = (
                module in FORBIDDEN_MODULES
                or root in FORBIDDEN_MODULES
                or dotted in FORBIDDEN_MODULES
            )
            if forbidden and not waived(lines, lineno, "network-import"):
                gate.add(
                    "network-import",
                    f"network module '{module}' is not allowed offline",
                    path,
                    lineno,
                )
        if re.search(r"^\s*import socket|^\s*from socket", text, re.MULTILINE):
            egress = [
                number
                for number, line in enumerate(lines, start=1)
                if SOCKET_EGRESS.search(line) and not waived(lines, number, "network-call")
            ]
            if egress:
                for number in egress:
                    gate.add(
                        "network-call", "socket operation that can reach the network", path, number
                    )
            else:
                gate.note(
                    f"{path.relative_to(REPO_ROOT)} imports socket for the local host name only"
                )
        for number, line in enumerate(lines, start=1):
            if NETWORK_CALL.search(line) and not waived(lines, number, "network-call"):
                gate.add("network-call", "outbound URL call in product code", path, number)


def check_dependencies(gate: Gate) -> None:
    pyproject = REPO_ROOT / "pyproject.toml"
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    runtime = data.get("project", {}).get("dependencies", [])
    names = {
        re.split(r"[<>=!~\[ ]", str(requirement), maxsplit=1)[0].lower() for requirement in runtime
    }
    forbidden = sorted(names & FORBIDDEN_DEPENDENCIES)
    for name in forbidden:
        gate.add(
            "network-dependency",
            f"runtime dependency '{name}' implies an online service",
            pyproject,
        )
    gate.note("runtime dependencies: " + ", ".join(sorted(names)))


def main(argv: list[str]) -> int:
    release, extras = parse_args(argv)
    if extras:
        print(f"unexpected argument(s): {' '.join(extras)}")
        return 2
    gate = Gate(
        name="offline operation", purpose="no network capability in the product", release=release
    )
    check_imports(gate)
    check_dependencies(gate)
    gate.note(f"source root inspected: {SRC_ROOT.relative_to(REPO_ROOT)}")
    return gate.report()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
