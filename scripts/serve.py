#!/usr/bin/env python3
"""
Start the preview on this computer and open it in Google Chrome.

    python3 scripts/serve.py            start (or reuse) the server, open Chrome
    python3 scripts/serve.py --no-open  start it, print the address, open nothing
    python3 scripts/serve.py --stop     stop it

The server runs in the background and outlives the Claude session, so the link
keeps working after the chat closes. It listens on 127.0.0.1 only: nothing on
the network can reach it.

It opens Google Chrome on purpose, never Claude's own built-in browser, so the
person ends up with a normal browser tab they can come back to. If Chrome is
not installed it falls back to their default browser.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
STATE = ROOT / ".preview-server.json"
LOG = ROOT / ".preview-server.log"
FIRST_PORT = 4321


INSTANCE = APP / "data" / ".instance"


def instance_id() -> str:
    """A random id for THIS folder, served by its own server. Two copies on one
    computer (a re-download, a second student) must never answer for each other."""
    if not INSTANCE.exists():
        INSTANCE.parent.mkdir(parents=True, exist_ok=True)
        import secrets
        INSTANCE.write_text(secrets.token_hex(8))
    return INSTANCE.read_text().strip()


def answering(port: int) -> bool:
    try:
        with urlopen("http://127.0.0.1:%d/data/.instance" % port, timeout=2) as r:
            return r.status == 200 and r.read().decode().strip() == instance_id()
    except Exception:
        return False


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def free_port() -> int:
    # Same address as last time when possible: their open tab and the sign-ups saved
    # in that browser stay where they were.
    try:
        last = json.loads(STATE.read_text()).get("port")
        if last and port_free(last):
            return last
    except Exception:
        pass
    for port in range(FIRST_PORT, FIRST_PORT + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit("No free port between %d and %d." % (FIRST_PORT, FIRST_PORT + 49))


def running_port():
    if STATE.exists():
        try:
            port = json.loads(STATE.read_text())["port"]
            if answering(port):
                return port
        except Exception:
            pass
    return None


def start() -> int:
    port = running_port()
    if port:
        return port
    instance_id()
    port = free_port()
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    with open(LOG, "ab") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(APP)],
            stdout=log, stderr=log, stdin=subprocess.DEVNULL, **kwargs,
        )
    for _ in range(40):
        if answering(port):
            STATE.write_text(json.dumps({"port": port, "pid": proc.pid}))
            return port
        time.sleep(0.25)
    raise SystemExit("The preview server did not start. See %s" % LOG)


def stop():
    if not STATE.exists():
        print("Not running.")
        return
    pid = json.loads(STATE.read_text()).get("pid")
    if not pid:
        print("Not running.")
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            os.kill(pid, 15)
    except Exception:
        pass
    try:
        STATE.write_text(json.dumps({"port": json.loads(STATE.read_text()).get("port"), "pid": None}))
    except Exception:
        STATE.unlink(missing_ok=True)
    print("Stopped.")


def open_in_chrome(url: str) -> str:
    system = platform.system()
    if system == "Darwin":
        if subprocess.run(["open", "-a", "Google Chrome", url], capture_output=True).returncode == 0:
            return "Google Chrome"
        subprocess.run(["open", url])
        return "your default browser"
    if system == "Windows":
        for exe in (
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ):
            if os.path.exists(exe):
                subprocess.Popen([exe, url])
                return "Google Chrome"
        os.startfile(url)  # type: ignore[attr-defined]
        return "your default browser"
    for exe in ("google-chrome", "google-chrome-stable", "chromium"):
        if shutil.which(exe):
            subprocess.Popen([exe, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Google Chrome"
    subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "your default browser"


def main() -> int:
    if "--stop" in sys.argv:
        stop()
        return 0
    port = start()
    url = "http://localhost:%d/" % port
    if "--no-open" in sys.argv:
        print(json.dumps({"url": url}))
        return 0
    where = open_in_chrome(url)
    print(json.dumps({"url": url, "openedIn": where}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
