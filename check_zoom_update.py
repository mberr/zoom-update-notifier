#!/usr/bin/env python
"""Check for zoom update and send a notification when it needs to be updated."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import time


def get_installed_version():
    """Get the installed version of Zoom."""
    re_version = re.compile(r"Version: ([\d.]+)$", flags=re.MULTILINE)
    p = subprocess.run(["apt", "show", "zoom"], capture_output=True)
    p.check_returncode()
    stdout = p.stdout.decode(encoding="utf8")
    if m := re_version.search(stdout):
        return m.group(1)
    else:
        print(f"Could not parse installed version from:\n{stdout}")
        exit(-1)


def get_latest_version(
    cache_path: pathlib.Path,
    force: bool,
    timeout: float,
):
    """Get the latest version of Zoom (via unofficial REST API.)"""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if (
        force
        or not cache_path.is_file()
        or time.time() - cache_path.stat().st_mtime > timeout
    ):
        cache_path.unlink(missing_ok=True)
        p = subprocess.run(
            ["curl", "https://zoom.us/rest/download?os=linux", "-s", "-o", cache_path]
        )
        p.check_returncode()
    data = json.loads(cache_path.read_text())
    return data["result"]["downloadVO"]["zoom"]["version"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-message", action="store_true")
    parser.add_argument("--direct-link", action="store_true")
    parser.add_argument(
        "--cache-path",
        type=pathlib.Path,
        default=pathlib.Path("~", ".cache", "zoom_version.json").expanduser(),
    )
    parser.add_argument("--timeout", type=float, default=24 * 60 * 60)
    args = parser.parse_args()

    version_installed = get_installed_version()
    if args.verbose:
        print("Installed:", version_installed)

    version_latest = get_latest_version(
        force=args.force, cache_path=args.cache_path, timeout=args.timeout
    )
    if args.verbose:
        print("Latest:   ", version_latest)
    if version_installed == version_latest:
        if args.verbose:
            print("Zoom is up-to-date")
        if args.no_message:
            exit(0)
        subprocess.run(
            ["notify-send", "-u", "low", f"Zoom is up-to-date ({version_installed})"]
        )
    else:
        if args.verbose:
            print("Zoom needs an update")
        if args.no_message:
            exit(-1)
        else:
            url = (
                f"https://zoom.us/client/{version_latest}/zoom_amd64.deb"
                if args.direct_link
                else "https://zoom.us/download"
            )
            subprocess.run(
                [
                    "notify-send",
                    "-u",
                    "critical",
                    f"'Zoom update available ({version_installed} -> {version_latest})'",
                    url,
                ]
            )


if __name__ == "__main__":
    main()
