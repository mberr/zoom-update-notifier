#!/usr/bin/env python
"""Check for zoom update and send a notification when it needs to be updated."""

from __future__ import annotations

import abc
import argparse
from collections.abc import Collection, Mapping
import dataclasses
import json
import pathlib
import re
import subprocess
import tempfile
import time
from typing import TypedDict


class PackageMetadata(TypedDict):
    version: str
    url: str


class Package(abc.ABC):
    name: str

    @abc.abstractmethod
    def get_latest_version(self) -> PackageMetadata:
        """Get the latest version."""
        raise NotImplementedError


@dataclasses.dataclass
class Zoom(Package):
    name: str = "zoom"

    def get_latest_version(self) -> PackageMetadata:
        """Get the latest version of Zoom (via unofficial REST API.)"""
        with tempfile.NamedTemporaryFile() as temporary_file:
            subprocess.run(
                [
                    "curl",
                    "https://zoom.us/rest/download?os=linux",
                    "-s",
                    "-o",
                    temporary_file.name,
                ],
                check=True,
            )
            data = json.loads(pathlib.Path(temporary_file.name).read_text())
        version = data["result"]["downloadVO"]["zoom"]["version"]
        url = f"https://zoom.us/client/{version}/zoom_amd64.deb"
        return PackageMetadata(version=version, url=url)


@dataclasses.dataclass
class VSCode(Package):
    name: str = "code"

    def get_latest_version(self) -> PackageMetadata:
        """Get the latest version of Zoom (via unofficial REST API.)"""
        with tempfile.NamedTemporaryFile() as temporary_file:
            subprocess.run(
                [
                    "curl",
                    "https://code.visualstudio.com/updates",
                    "-s",
                    "-L",
                    "-o",
                    temporary_file.name,
                ],
                check=True,
            )
            text = pathlib.Path(temporary_file.name).read_text()
            m = re.search(
                r'<a href="(https:\/\/update\.code\.visualstudio\.com\/([^/]+?)\/linux-deb-x64\/stable)">deb<\/a>',
                text,
                flags=re.MULTILINE,
            )
            url = m.group(1)
            version = m.group(2)
            return PackageMetadata(version=version, url=url)


@dataclasses.dataclass
class Manager:
    packages: Package | Collection[Package]
    download: bool = True
    notification: bool = True
    verbose: bool = True
    timeout: float | int = 24 * 60 * 60
    cache_root: pathlib.Path = pathlib.Path.home().joinpath(
        ".cache", "simple_package_manager"
    )
    download_root: pathlib.Path = pathlib.Path(tempfile.gettempdir(), "updates")
    _packages: Mapping[str, Package] = dataclasses.field(init=False, repr=False)

    def __post_init__(self):
        packages = self.packages
        if isinstance(packages, Package):
            packages = [packages]
        _packages = {}
        for package in packages:
            _packages[package.name] = package
        self._packages = _packages

    def get_installed_version(self, name: str) -> str:
        """Get the installed version."""
        re_version = re.compile(r"Version: ([\d.-]+)$", flags=re.MULTILINE)
        p = subprocess.run(["apt", "show", name], capture_output=True)
        p.check_returncode()
        stdout = p.stdout.decode(encoding="utf8")
        if m := re_version.search(stdout):
            return m.group(1).split("-")[0]
        else:
            print(f"Could not parse installed version from:\n{stdout}")
            exit(-1)

    def get_latest_version(self, name: str, force: bool = False) -> PackageMetadata:
        """Get the latest version."""
        cache_path = self.cache_root.joinpath(name).with_suffix(".json")
        if (
            force
            or not cache_path.is_file()
            or time.time() - cache_path.stat().st_mtime > self.timeout
        ):
            self.cache_root.mkdir(parents=True, exist_ok=True)
            cache_path.unlink(missing_ok=True)
            data = self._packages[name].get_latest_version()
            with cache_path.open(mode="w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        with cache_path.open() as f:
            data = json.load(f)
        return data

    def _check(self, name: str, force: bool) -> None:
        version_installed = self.get_installed_version(name)
        if self.verbose:
            print(f"# Package: {name!r}")
            print("Installed:", version_installed)
        meta = self.get_latest_version(name=name, force=force)
        version_latest = meta["version"]
        if self.verbose:
            print("Latest:   ", version_latest)
        if version_installed == version_latest:
            if self.verbose:
                print(f"{name!r} is up-to-date")
            if not self.notification:
                return
            subprocess.run(
                [
                    "notify-send",
                    "-u",
                    "low",
                    f"{name} is up-to-date ({version_installed})",
                ]
            )
        else:
            if self.verbose:
                print("Zoom needs an update")
            if not self.notification:
                exit(-1)
            else:
                url = meta["url"]
                if self.download_root:
                    output_path = pathlib.Path(self.download_root).joinpath(
                        f"{name}_{version_latest}.deb"
                    )
                    output_path.parent.mkdir(exist_ok=True, parents=True)
                    subprocess.run(["wget", "-O", str(output_path), url], check=True)
                    message = (
                        f"'{name} update available ({version_installed} -> {version_latest})'",
                        output_path,
                    )
                else:
                    message = (
                        f"'{name} update available ({version_installed} -> {version_latest})'",
                        url,
                    )
                subprocess.run(["notify-send", "-u", "critical", *message])

    def check(self, force: bool = False):
        for name in self._packages:
            self._check(name=name, force=force)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-message", action="store_true")
    parser.add_argument("--direct-link", action="store_true")
    parser.add_argument(
        "--cache-root",
        type=pathlib.Path,
        default=pathlib.Path("~", ".cache", "simple_package_manager").expanduser(),
    )
    parser.add_argument("--timeout", type=float, default=24 * 60 * 60)
    parser.add_argument("--download-root", type=str, default=tempfile.gettempdir())
    args = parser.parse_args()
    cache_root = pathlib.Path(args.cache_root)
    manager = Manager(
        packages=[Zoom(), VSCode()], cache_root=cache_root, timeout=args.timeout
    )
    manager.check(force=args.force)


if __name__ == "__main__":
    main()
