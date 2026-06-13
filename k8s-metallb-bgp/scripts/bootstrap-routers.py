#!/usr/bin/env python3
"""Bootstrap R1-R4 over their GNS3 console ports so Ansible can SSH in.

GNS3 exposes each node's console as a plain TCP port on the server. This
script implements a minimal expect loop over raw sockets (telnetlib left the
stdlib in Python 3.13), waits for each router to finish booting, declines the
initial-config dialog, and pastes the SSH bootstrap: hostname, domain, RSA
keys, admin/admin credentials, vty SSH, and the Gi0/4 management address.

Console ports are discovered from the GNS3 API, so run build-topology.py
(or have the project open) first.

Usage:
    ./bootstrap-routers.py [--server http://10.10.10.2:3080] [--routers R1 R2] [--debug]
"""

import argparse
import json
import re
import socket
import sys
import time
import urllib.request
from urllib.parse import urlparse

PROJECT_NAME = "k8s-metallb-bgp"
MGMT_IP = {"R1": "192.168.0.1", "R2": "192.168.0.2",
           "R3": "192.168.0.3", "R4": "192.168.0.4"}

BOOTSTRAP = """\
enable
configure terminal
hostname {name}
ip domain-name lab
username admin privilege 15 password admin
line vty 0 15
 login local
 transport input ssh
interface GigabitEthernet0/4
 ip address {ip} 255.255.255.0
 no shutdown
exit
"""


class Console:
    def __init__(self, host, port, log_prefix, debug=False):
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(2)
        self.buf = b""
        self.prefix = log_prefix
        self.debug = debug

    def read_until(self, patterns, timeout):
        """Wait until any regex in `patterns` matches the stream."""
        deadline = time.monotonic() + timeout
        compiled = [re.compile(p.encode()) for p in patterns]
        while time.monotonic() < deadline:
            for i, rx in enumerate(compiled):
                if rx.search(self.buf):
                    matched = self.buf
                    self.buf = b""
                    return i, matched
            try:
                chunk = self.sock.recv(4096)
                if chunk:
                    if self.debug:
                        sys.stderr.write(f"[{self.prefix}] rx: {chunk!r}\n")
                    self.buf += chunk
            except socket.timeout:
                pass
        raise TimeoutError(f"{self.prefix}: none of {patterns} seen in {timeout}s")

    def send(self, line=""):
        self.sock.sendall(line.encode() + b"\r")

    def close(self):
        self.sock.close()


def get_consoles(server):
    compute_host = urlparse(server).hostname or "127.0.0.1"

    def api(path):
        with urllib.request.urlopen(f"{server}/v2{path}") as resp:
            return json.loads(resp.read())

    project = next((p for p in api("/projects") if p["name"] == PROJECT_NAME), None)
    if project is None:
        sys.exit(f"project {PROJECT_NAME} not found on {server}")
    out = {}
    for n in api(f"/projects/{project['project_id']}/nodes"):
        if n["name"] in MGMT_IP:
            host = n.get("console_host")
            if not host or host in ("0.0.0.0", "::"):
                host = compute_host
            out[n["name"]] = (host, n["console"])
    return out


def wait_for_prompt(con, name, total_timeout=420, poke_interval=10):
    """Re-poke the console every pass and watch for a usable state.

    A router that already finished booting sits silent and will not volunteer a
    fresh prompt, so a single poke followed by passive listening waits out the
    whole timeout. Sending a newline each pass forces a quiet booted box to
    echo its prompt. The short per-pass timeout is what makes re-poking possible
    inside the overall deadline.
    """
    patterns = [r"initial configuration dialog\? \[yes/no\]:",
                r"Press RETURN to get started",
                r"[\w.\-]+[>#]\s*$"]
    deadline = time.monotonic() + total_timeout
    while time.monotonic() < deadline:
        con.send()  # prod every pass, not just once
        try:
            idx, _ = con.read_until(patterns, timeout=poke_interval)
        except TimeoutError:
            continue  # silent this pass; loop and poke again
        if idx == 0:
            con.send("no")
        elif idx == 1:
            con.send()
        else:
            return  # plain prompt -> booted and at exec
    raise TimeoutError(f"{name}: no prompt after {total_timeout}s")


def bootstrap(name, host, port, debug=False):
    con = Console(host, port, name, debug=debug)
    print(f"[{name}] connected to console {host}:{port}")

    wait_for_prompt(con, name)
    print(f"[{name}] prompt up, pasting bootstrap")

    for line in BOOTSTRAP.format(name=name, ip=MGMT_IP[name]).splitlines():
        con.send(line)
        time.sleep(0.3)

    # Confirm the paste landed before the crypto step, and resync the buffer.
    # After the trailing `exit` we should be at `{name}(config)#`.
    con.read_until([re.escape(name) + r"\(config\)#\s*$"], timeout=20)

    # RSA keys: needs hostname + domain set first, takes a few seconds.
    con.send("crypto key generate rsa modulus 1024")
    idx, _ = con.read_until([r"\[OK\]", r"replace them\? \[yes/no\]:"], timeout=90)
    if idx == 1:
        con.send("no")  # keys already exist from a previous run
        con.read_until([r"#"], timeout=15)
    con.send("end")
    con.read_until([r"#"], timeout=15)
    print(f"[{name}] bootstrap complete")
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://localhost:3080")
    ap.add_argument("--routers", nargs="*", default=list(MGMT_IP))
    ap.add_argument("--debug", action="store_true",
                    help="echo raw console bytes to stderr")
    args = ap.parse_args()

    consoles = get_consoles(args.server)
    failed = []
    for name in args.routers:
        try:
            host, port = consoles[name]
            bootstrap(name, host, port, debug=args.debug)
        except (TimeoutError, OSError, KeyError) as exc:
            print(f"[{name}] FAILED: {exc}", file=sys.stderr)
            failed.append(name)

    if failed:
        sys.exit(f"bootstrap failed for: {', '.join(failed)} -- "
                 "rerun with --routers " + " ".join(failed))
    print("all routers bootstrapped; SSH should answer on 192.168.0.1-4")


if __name__ == "__main__":
    main()
