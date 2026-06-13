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
    ./bootstrap-routers.py [--server http://10.10.10.2:3080] [--routers R1 R2]
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
    def __init__(self, host, port, log_prefix):
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(2)
        self.buf = b""
        self.prefix = log_prefix

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


def bootstrap(name, host, port):
    con = Console(host, port, name)
    print(f"[{name}] connected to console {host}:{port}")

    # Poke the console, then wait out the boot. IOSv can take several
    # minutes; the autoconfig dialog and the plain prompt are both exits.
    con.send()
    while True:
        idx, _ = con.read_until(
            [r"initial configuration dialog\? \[yes/no\]:",
             r"Press RETURN to get started",
             r"[\w-]+[>#]\s*$"],
            timeout=420,
        )
        if idx == 0:
            con.send("no")
        elif idx == 1:
            con.send()
        else:
            break
    print(f"[{name}] prompt up, pasting bootstrap")

    for line in BOOTSTRAP.format(name=name, ip=MGMT_IP[name]).splitlines():
        con.send(line)
        time.sleep(0.3)

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
    args = ap.parse_args()

    consoles = get_consoles(args.server)
    failed = []
    for name in args.routers:
        try:
            host, port = consoles[name]
            bootstrap(name, host, port)
        except (TimeoutError, OSError, KeyError) as exc:
            print(f"[{name}] FAILED: {exc}", file=sys.stderr)
            failed.append(name)

    if failed:
        sys.exit(f"bootstrap failed for: {', '.join(failed)} -- "
                 "rerun with --routers " + " ".join(failed))
    print("all routers bootstrapped; SSH should answer on 192.168.0.1-4")


if __name__ == "__main__":
    main()
